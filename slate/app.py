from aiohttp import web

from slate.graph import init_graph
from slate.routes import setup_routes
from slate.slack import init_slack
from slate.metrics import setup_prometheus, prometheus_middleware

def make_app() -> web.Application:
    app = web.Application(middlewares=[prometheus_middleware])

    app.on_startup.append(init_graph)
    app.on_startup.append(init_slack)

    setup_routes(app)
    setup_prometheus(app, 'slate')

    return app
