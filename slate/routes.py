from aiohttp import web

from slate import Settings
from slate.views import health, ingest


def setup_routes(app: web.Application):
    app.router.add_post('/ingest/', ingest, name='ingest')
    app.router.add_get('/health/', health, name='health')

    if Settings.dev:
        from slate.views import channel, replay, history

        app.router.add_get('/history/', history, name='history')
        app.router.add_get('/channel/{channel_id:[A-Z0-9]+}/', channel, name='channel')
        app.router.add_get('/replay/{event_id:[A-Z0-9]+}/', replay, name='replay')
