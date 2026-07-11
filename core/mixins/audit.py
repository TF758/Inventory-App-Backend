"""Immutable audit logging hooks for DRF views."""

from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils.text import capfirst

from core.models.audit import AuditLog


class AuditMixin:
    """Record CRUD and domain audit events after successful transactions."""

    @staticmethod
    def _empty_scope():
        return {
            "room": None,
            "room_name": None,
            "location": None,
            "location_name": None,
            "department": None,
            "department_name": None,
        }

    def _resolve_scope(self, target):
        if not target:
            return self._empty_scope()

        scope = self._empty_scope()

        room = getattr(target, "room", None)
        location = getattr(target, "location", None)
        department = getattr(target, "department", None)

        if room:
            location = getattr(room, "location", None)
            department = getattr(location, "department", None) if location else None
        elif location:
            department = getattr(location, "department", None)

        scope.update(
            room=room,
            room_name=getattr(room, "name", None),
            location=location,
            location_name=getattr(location, "name", None),
            department=department,
            department_name=getattr(department, "name", None),
        )
        return scope

    @staticmethod
    def _get_target_label(target):
        if not target:
            return None

        audit_label = getattr(target, "audit_label", None)
        if callable(audit_label):
            return audit_label()

        return str(target)

    @staticmethod
    def _get_target_model(target):
        if not target:
            return None
        return capfirst(target.__class__.__name__)

    def _log_audit(
        self,
        event_type,
        *,
        target=None,
        description="",
        metadata=None,
    ):
        request = getattr(self, "request", None)
        user = getattr(request, "user", None) if request else None

        if user and user.is_anonymous:
            user = None

        scope = self._resolve_scope(target)

        def create_log():
            AuditLog.objects.create(
                user=user,
                user_public_id=getattr(user, "public_id", None),
                user_email=getattr(user, "email", None),
                event_type=event_type,
                description=description,
                metadata=metadata or {},
                target_model=self._get_target_model(target),
                target_id=getattr(target, "public_id", None),
                target_name=self._get_target_label(target),
                department=scope["department"],
                department_name=scope["department_name"],
                location=scope["location"],
                location_name=scope["location_name"],
                room=scope["room"],
                room_name=scope["room_name"],
                ip_address=request.META.get("REMOTE_ADDR") if request else None,
                user_agent=(
                    request.META.get("HTTP_USER_AGENT", "") if request else ""
                ),
            )

        if getattr(settings, "IS_TESTING", False):
            create_log()
        else:
            transaction.on_commit(create_log)

    def audit(
        self,
        event_type,
        *,
        target=None,
        description="",
        metadata=None,
    ):
        """Record an explicit business or domain audit event."""
        self._log_audit(
            event_type,
            target=target,
            description=description,
            metadata=metadata,
        )

    def perform_create(self, serializer):
        obj = serializer.save()
        self._log_audit(AuditLog.Events.MODEL_CREATED, target=obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self._log_audit(AuditLog.Events.MODEL_UPDATED, target=obj)

    def perform_destroy(self, instance):
        self._log_audit(AuditLog.Events.MODEL_DELETED, target=instance)
        instance.delete()
