from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope = dict(scope) 

        scope["user"] = await self.get_anonymous_user()

        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token")

        if token:
            user = await self.get_user(token[0])
            if user is not None:
                scope["user"] = user

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser
        return AnonymousUser()

    @database_sync_to_async
    def get_user(self, raw_token):
        from db_inventory.authentication import SessionJWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken
        from rest_framework.exceptions import AuthenticationFailed
        from django.contrib.auth.models import AnonymousUser

        auth = SessionJWTAuthentication()

        try:
            validated_token = auth.get_validated_token(raw_token)
            return auth.get_user(validated_token)
        except (InvalidToken, AuthenticationFailed):
            return AnonymousUser()
