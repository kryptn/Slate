import platform

from aiohttp import web
from aiohttp.web import json_response

from slate import Settings


async def ingest(request: web.Request) -> web.Response:
    payload = await request.json()
    if payload.pop('token', None) != Settings.slack_verification_token:
        return web.Response(status=401, reason='invalid token')

    if payload['type'] == 'url_verification':
        return json_response({'challenge': payload['challenge']})

    request.app.loop.create_task(request.app.slack.handle(payload))
    return web.Response(status=200)


async def history(request: web.Request) -> web.Response:
    if 'raw' in request.query:
        return json_response(request.app.slack.history)
    q = "match (m:Message) return m order by m.event_ts"
    return json_response(request.app.graph.run(q).data())


async def metrics(request: web.Request) -> web.Response:
    return json_response({})


async def health(request: web.Request) -> web.Response:
    count = request.app.graph.run("match (n:Slack) return count(n) as node_count").data()[0]
    check = {'healthy': True, 'node': platform.node()}
    check.update(count)
    return json_response(check)
