from aiohttp import web

from slate import Settings
from slate.views import health, ingest, history, channel


def setup_routes(app: web.Application):
    app.router.add_post('/ingest/', ingest, name='ingest')
    app.router.add_get('/health/', health, name='health')

    if Settings.dev:
        app.router.add_get('/history/', history, name='history')
        app.router.add_get('/channel/{channel_id:[A-Z0-9]+}/', channel, name='channel')
