"""General DRF viewset behavior."""

from __future__ import annotations

from rest_framework.response import Response


class LightEndpointMixin:
    """Return a capped, unpaginated list when pagination is disabled."""

    light_limit = 20

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if self.pagination_class is None:
            queryset = queryset[: self.light_limit]
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
