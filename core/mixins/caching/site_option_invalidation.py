"""Explicit DRF mutation hooks for site-option cache invalidation."""

from __future__ import annotations

import logging

from sites.services.option_cache import SiteOptionCacheService

logger = logging.getLogger("arms.scope_cache")


class SiteOptionInvalidationMixin:
    """Rotate the global site-options generation after successful CRUD writes.

    Place this mixin *before* ``AuditMixin`` in the viewset base-class list.
    It calls ``super().perform_*()``, allowing ``AuditMixin`` to perform the
    actual save/delete and register its audit callback first. Invalidation is
    then registered against the same successful transaction.

    This is deliberately explicit: no model signals and no model-layer cache
    coupling. Bulk imports, management commands, admin actions, and direct ORM
    writes must call ``SiteOptionCacheService.invalidate_on_commit()`` once at
    their own mutation boundary.
    """

    site_option_cache_resource: str | None = None
    site_option_cache_alias: str | None = None

    def get_site_option_cache_resource(self) -> str:
        resource = str(self.site_option_cache_resource or "").strip()
        if not resource:
            raise ValueError(
                f"{self.__class__.__name__} must define "
                "site_option_cache_resource"
            )
        return resource

    def get_site_option_cache_alias(self) -> str | None:
        return self.site_option_cache_alias

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        self.schedule_site_option_invalidation(
            action="created",
            instance=instance,
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        self.schedule_site_option_invalidation(
            action="updated",
            instance=instance,
        )

    def perform_destroy(self, instance):
        # Capture identity before AuditMixin deletes the row.
        object_public_id = getattr(instance, "public_id", None)
        object_pk = getattr(instance, "pk", None)

        super().perform_destroy(instance)

        self.schedule_site_option_invalidation(
            action="deleted",
            instance=None,
            object_public_id=object_public_id,
            object_pk=object_pk,
        )

    def schedule_site_option_invalidation(
        self,
        *,
        action: str,
        instance=None,
        object_public_id=None,
        object_pk=None,
    ) -> None:
        resource = self.get_site_option_cache_resource()
        public_id = object_public_id or getattr(instance, "public_id", None)
        pk = object_pk or getattr(instance, "pk", None)
        actor_public_id = getattr(
            getattr(getattr(self, "request", None), "user", None),
            "public_id",
            None,
        )

        identity = public_id or pk or "unknown"
        reason = (
            f"{resource}_{action}:object={identity}:"
            f"actor={actor_public_id or 'system'}"
        )

        logger.info(
            "SITE OPTION CACHE MUTATION OBSERVED | resource=%s action=%s "
            "object_public_id=%s object_pk=%s actor_public_id=%s "
            "view=%s",
            resource,
            action,
            public_id,
            pk,
            actor_public_id,
            self.__class__.__name__,
        )

        SiteOptionCacheService.invalidate_on_commit(
            reason=reason,
            cache_alias=self.get_site_option_cache_alias(),
        )
