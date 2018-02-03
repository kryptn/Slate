from aiohttp import web, ClientSession
from yarl import URL

from slate import Settings


def callback_uri(request: web.Request) -> str:
    redirect_path = request.app.router['oauth-verify'].url_for().path
    redirect_uri = URL(Settings.hostname).with_path(redirect_path)
    return str(redirect_uri)


def oauth_authorize_url(request: web.Request) -> str:
    authorize_url = URL('https://slack.com/oauth/authorize').with_query({
        'client_id': Settings.slack_client_id,
        'scope': ','.join(Settings.read_only_scopes),
        'redirect_uri': callback_uri(request)
    })
    return str(authorize_url)


async def oauth_redirect(request: web.Request) -> web.Response:
    slack_oauth_url = oauth_authorize_url(request)
    return web.HTTPFound(slack_oauth_url)


async def install(request: web.Request) -> web.Response:
    slack_oauth_url = oauth_authorize_url(request)
    button = f"""
    <a href="{slack_oauth_url}">
      <img alt="Add to Slack" height="40" width="139" 
        src="https://platform.slack-edge.com/img/add_to_slack.png" 
        srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" />
    </a>"""
    return web.Response(body=button, content_type='text/html')


async def oauth_verify(request: web.Request) -> web.Response:
    code = request.query.get('code', None)
    if not code:
        return web.HTTPBadRequest()

    slack_oauth_access = URL('https://slack.com/api/oauth.access')
    payload = {
        'client_id': Settings.slack_client_id,
        'client_secret': Settings.slack_client_secret,
        'code': code,
        'redirect_uri': callback_uri(request)
    }

    async with ClientSession() as client:
        resp = await client.post(slack_oauth_access, data=payload)
        data = await resp.json()

    await request.app.slack_oauth_callback(data, status=resp.status)
    return web.json_response({'ok': True}, status=200)


def init_slack_oauth_flow(app, callback=None):
    app.router.add_get('/oauth/redirect/', oauth_redirect, name='oauth-redirect')
    app.router.add_get('/oauth/verify/', oauth_verify, name='oauth-verify')
    app.router.add_get('/install/', install, name='install')

    if not callback:
        async def print_callback(data, status):
            print(data, status)

        callback = print_callback

    app.slack_oauth_callback = callback
