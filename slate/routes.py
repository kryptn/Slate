from aiohttp import web

from slate import Settings
from slate.views import health, ingest


def setup_routes(app: web.Application):
    app.router.add_post('/ingest/', ingest, name='ingest')
    app.router.add_get('/health/', health, name='health')

    if Settings.dev:
        from slate.views import channel, history, toggle_repeat

        app.router.add_get('/toggle-repeat/{host}', toggle_repeat, name='toggle-repeat')
        app.router.add_get('/history/', history, name='history')
        app.router.add_get('/channel/{channel_id:[A-Z0-9]+}/', channel, name='channel')
