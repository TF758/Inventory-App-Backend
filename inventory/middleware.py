from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = await self.get_anonymous_user()

        token = self.extract_token(scope)

        if token:
            user = await self.get_user(token)
            if user:
                scope["user"] = user

        return await super().__call__(scope, receive, send)

    @staticmethod
    def extract_token(scope):
        """Resolve JWTs without exposing them in production URLs."""

        subprotocols = scope.get("subprotocols", [])
        if len(subprotocols) == 2 and subprotocols[0] == "jwt":
            return subprotocols[1]

        if not settings.WEBSOCKET_ALLOW_QUERY_TOKEN:
            return None

        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token")
        return token_list[0] if token_list else None

    @database_sync_to_async
    def get_anonymous_user(self):
        return AnonymousUser()

    @database_sync_to_async
    def get_user(self, raw_token):
        from core.authentication import SessionJWTAuthentication
        from rest_framework.exceptions import AuthenticationFailed
        from rest_framework_simplejwt.exceptions import InvalidToken

        auth = SessionJWTAuthentication()

        try:
            validated_token = auth.get_validated_token(raw_token)
            return auth.get_user(validated_token)
        except (InvalidToken, AuthenticationFailed):
            return AnonymousUser()
