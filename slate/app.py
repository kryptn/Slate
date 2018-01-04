from aiohttp import web

from slate.graph import init_graph
from slate.routes import setup_routes
from slate.slack import init_slack


def make_app() -> web.Application:
    app = web.Application()

    app.on_startup.append(init_graph)
    app.on_startup.append(init_slack)

    setup_routes(app)

    return app
