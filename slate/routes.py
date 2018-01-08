from aiohttp import web

from slate.views import health, ingest, history, channel, oauth_redirect, oauth_verify, install


def setup_routes(app: web.Application):
    app.router.add_post('/ingest/', ingest, name='ingest')
    app.router.add_get('/health/', health, name='health')
    app.router.add_get('/history/', history, name='history')

    app.router.add_get('/channel/{channel_id}/', channel, name='channel')

    app.router.add_get('/oauth/redirect/', oauth_redirect, name='oauth-redirect')
    app.router.add_get('/oauth/verify/', oauth_verify, name='oauth-verify')
    app.router.add_get('/install/', install, name='install')
