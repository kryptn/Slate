from aiohttp import web

from slate.views import health, ingest, history


def setup_routes(app: web.Application):
    app.router.add_post('/ingest/', ingest, name='ingest')
    app.router.add_get('/health/', health, name='health')
    app.router.add_get('/history/', history, name='history')
