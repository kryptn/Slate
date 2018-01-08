import json
import platform

from aiohttp import web, ClientSession
from aiohttp.web import json_response
from yarl import URL

from slate import Settings


def oauth_redirect_path(request: web.Request) -> str:
    redirect_path = request.app.router['oauth-verify'].url_for().path
    redirect_uri = URL(Settings.hostname).with_path(redirect_path)
    return str(redirect_uri)


async def ingest(request: web.Request) -> web.Response:
    payload = await request.json()
    if payload.pop('token', None) != Settings.slack_verification_token:
        return web.Response(status=401, reason='invalid token')

    if payload['type'] == 'url_verification':
        return json_response({'challenge': payload['challenge']})

    request.app.loop.create_task(request.app.slack.handle(payload))
    return web.Response(status=200)


async def history(request: web.Request) -> web.Response:
    q = 'match (e:IngestEvent) with e order by e.event_time return collect(e) as events'
    result = request.app.graph.run(q)
    data = []
    for event in result.data()[0]['events']:
        item = dict(event)
        item['data'] = json.loads(item['data'])
        data.append(item)
    return json_response(data)


async def channel(request: web.Request) -> web.Response:
    channel = request.match_info['channel_id']

    cypher = f"""    
    match (message:Message {{channel:'{channel}'}}) 
      where message.hidden is null and message.thread_ts is null
    
    optional match (reply:Message)-[:REPLY_TO]->(message)
      where reply.hidden is null
    with message, collect(reply) as replies
    
    optional match (reaction:Reaction)-->(message)
    with message, replies, collect(reaction) as reactions
    
    return message, replies, reactions
    """
    result = request.app.graph.run(cypher)
    data = result.data()

    return json_response(sorted(data, key=lambda x: x['message']['event_ts']))


async def oauth_redirect(request: web.Request) -> web.Response:
    slack_oauth = URL('https://slack.com/oauth/authorize').with_query({
        'client_id': Settings.slack_client_id,
        'scope': ','.join(Settings.read_only_scopes),
        'redirect_uri': oauth_redirect_path(request)
    })
    return web.HTTPFound(slack_oauth)


async def oauth_verify(request: web.Request) -> web.Response:
    code = request.query.get('code', None)
    if not code:
        return web.HTTPBadRequest()

    slack_oauth_access = URL('https://slack.com/api/oauth.access')
    payload = {
        'client_id': Settings.slack_client_id,
        'client_secret': Settings.slack_client_secret,
        'code': code,
        'redirect_uri': oauth_redirect_path(request)
    }
    async with ClientSession() as client:
        resp = await client.post(slack_oauth_access, data=payload)
        data = await resp.json()
    await request.app.slack.authorize(data)
    return json_response({'ok': True}, status=200)


async def install(request: web.Request) -> web.Response:
    slack_oauth = URL('https://slack.com/oauth/authorize').with_query({
        'client_id': Settings.slack_client_id,
        'scope': ','.join(Settings.read_only_scopes),
        'redirect_uri': oauth_redirect_path(request)
    })
    button = f"""
    <a href="{slack_oauth}">
      <img alt="Add to Slack" height="40" width="139" 
        src="https://platform.slack-edge.com/img/add_to_slack.png" 
        srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
    </a>"""
    return web.Response(body=button, content_type='text/html')


async def health(request: web.Request) -> web.Response:
    node_count = request.app.graph.run("match (n:Slack) return count(n) as node_count").data()[0]
    edge_count = request.app.graph.run("match (:Slack)-[r]-(:Slack) return count(r) as edge_count").data()[0]
    check = {'healthy': True, 'node': platform.node()}
    check.update(node_count)
    check.update(edge_count)
    return json_response(check)
