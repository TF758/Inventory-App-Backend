"""Serializer-selection helpers for DRF viewsets."""

from __future__ import annotations


class ListDetailSerializerMixin:
    """Use optional specialized serializers for list and retrieve actions."""

    list_serializer_class = None
    detail_serializer_class = None

    def get_serializer_class(self):
        if self.action == "retrieve" and self.detail_serializer_class:
            return self.detail_serializer_class

        if self.action == "list" and self.list_serializer_class:
            return self.list_serializer_class

        return super().get_serializer_class()
