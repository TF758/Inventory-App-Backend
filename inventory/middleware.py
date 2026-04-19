from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = await self.get_anonymous_user()

        token = None

        # --- Preferred: Sec-WebSocket-Protocol ---
        subprotocols = scope.get("subprotocols", [])
        if len(subprotocols) == 2 and subprotocols[0] == "jwt":
            token = subprotocols[1]

        # --- Fallback: query string ---
        if not token:
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token_list = params.get("token")
            if token_list:
                token = token_list[0]

        if token:
            user = await self.get_user(token)
            if user:
                scope["user"] = user

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_anonymous_user(self):
        return AnonymousUser()

    @database_sync_to_async
    def get_user(self, raw_token):
        from core.authentication import SessionJWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken
        from rest_framework.exceptions import AuthenticationFailed

        auth = SessionJWTAuthentication()

        try:
            validated_token = auth.get_validated_token(raw_token)
            return auth.get_user(validated_token)
        except (InvalidToken, AuthenticationFailed):
            return AnonymousUser()