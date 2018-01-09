from aiohttp import web

from slate.graph import init_graph
from slate.routes import setup_routes
from slate.slack import init_slack
from slate.oauth import init_slack_oauth_flow
from slate.metrics import setup_prometheus, prometheus_middleware

def make_app() -> web.Application:
    app = web.Application(middlewares=[prometheus_middleware])

    app.on_startup.append(init_graph)
    app.on_startup.append(init_slack)

    async def auth_callback(data: dict, status: int):
        # this is what the slack oauth flow returns
        # will send to amqp soon
        if status == 200:
            await app.slack.authorize(data)

    init_slack_oauth_flow(app, auth_callback)
    setup_routes(app)
    setup_prometheus(app, 'slate')

    return app
