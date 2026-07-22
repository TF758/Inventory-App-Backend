"""Database and websocket notification helpers."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction

from core.models.notifications import Notification


class NotificationMixin:
    """Create user notifications only after the surrounding transaction commits."""

    def notify(
        self,
        *,
        recipient,
        notif_type,
        title,
        message,
        level=Notification.Level.INFO,
        entity=None,
        actor=None,
        meta=None,
    ):
        # ``actor`` remains in the signature for backward compatibility.
        del actor

        if not recipient or recipient.is_anonymous:
            return

        def create_notification():
            notification = Notification.objects.create(
                recipient=recipient,
                type=notif_type,
                level=level,
                title=title,
                message=message,
                entity_type=(
                    entity.__class__.__name__.lower() if entity else None
                ),
                entity_id=getattr(entity, "public_id", None),
                meta=meta,
            )

            if getattr(settings, "IS_TESTING", False):
                return

            channel_layer = get_channel_layer()
            if not channel_layer:
                return

            payload = {
                "public_id": notification.public_id,
                "type": notification.type,
                "level": notification.level,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "entity": (
                    {
                        "type": notification.entity_type,
                        "id": notification.entity_id,
                    }
                    if notification.entity_id
                    else None
                ),
                "meta": notification.meta,
            }

            async_to_sync(channel_layer.group_send)(
                f"user_{recipient.public_id}",
                {
                    "type": "notification",
                    "payload": payload,
                },
            )

        if getattr(settings, "IS_TESTING", False):
            create_notification()
        else:
            transaction.on_commit(create_notification)
