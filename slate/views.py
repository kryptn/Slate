import json
import platform

from aiohttp import web, ClientSession
from aiohttp.web import json_response

from slate import Settings


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

async def toggle_repeat(request: web.Request) -> web.Response:
    target = request.match_info.get('host', None)
    q = f"""
    merge (n:Slack:RepeatTarget {{destination: "{target}" }})
      on create set n.enabled=true
      on match set n.enabled = not n.enabled
    return n as target
    """
    result = request.app.graph.run(q)
    return json_response(result.data())

async def repeat(payload, destination):
    with ClientSession() as client:
        return await client.post(destination, data=payload)

async def ingest(request: web.Request) -> web.Response:
    payload = await request.json()
    if payload.pop('token', None) != Settings.slack_verification_token:
        return web.Response(status=401, reason='invalid token')

    if payload['type'] == 'url_verification':
        return json_response({'challenge': payload['challenge']})

    if Settings.slack_event_repeater:
        q = 'match (n:Slack:RepeatTarget {enabled: true}) return n.destination as destination'
        targets = request.app.graph.run(q)
        for target in targets.data():
            await repeat(payload, target['destination'])
            return web.Response(status=200)

    request.app.loop.create_task(request.app.slack.handle(payload))
    return web.Response(status=200)


async def health(request: web.Request) -> web.Response:
    node_count = request.app.graph.run("match (n:Slack) return count(n) as node_count").data()[0]
    edge_count = request.app.graph.run("match (:Slack)-[r]-(:Slack) return count(r) as edge_count").data()[0]
    check = {'healthy': True, 'node': platform.node()}
    check.update(node_count)
    check.update(edge_count)
    return json_response(check)
