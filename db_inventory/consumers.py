import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        if not user or user.is_anonymous:
            await self.close(code=4401)
            return

        if not hasattr(user, "public_id"):
            await self.close(code=4401)
            return

        self.group_name = f"user_{user.public_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get("user")

        if user and not user.is_anonymous:
            await self.channel_layer.group_discard(
                f"user_{user.public_id}",
                self.channel_name,
            )

    async def notification(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
