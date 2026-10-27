from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from config.cognito_auth import resolve_token_user


class JWTAuthMiddleware(BaseMiddleware):
    """Authenticate WebSocket connections with a Cognito access token.

    The same token rules as the REST API apply (RS256 signature verified
    against the Cognito JWKS; fake tokens under the test-suite backend).
    """

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope["user"] = AnonymousUser()
        query = parse_qs(scope.get("query_string", b"").decode())
        token = query.get("token", [None])[0]

        if token:
            # DB access must happen off the event loop; token decoding runs in
            # the same worker thread for simplicity and identical error rules.
            scope["user"] = await database_sync_to_async(resolve_token_user)(token)

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
