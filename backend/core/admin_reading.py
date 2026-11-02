"""Readable content pages keep Django's existing edit and permission checks."""
from django.core.exceptions import PermissionDenied
from django.http import Http404


class ReadingAdminMixin:
    reading_kind = None

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET" and request.GET.get("_edit") != "1" and not request.GET.get("_popup"):
            obj = self.get_object(request, object_id)
            if obj is None:
                raise Http404
            if not self.has_view_or_change_permission(request, obj):
                raise PermissionDenied
            from .guidance_views import document_reading
            return document_reading(request, obj, self.reading_kind, self)
        return super().change_view(request, object_id, form_url, extra_context)


class InteractionReadingAdminMixin:
    """Read conversation and Q&A content before opening its administrative form."""

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET" and request.GET.get("_edit") != "1" and not request.GET.get("_popup"):
            obj = self.get_object(request, object_id)
            if obj is None:
                raise Http404
            if not self.has_view_or_change_permission(request, obj):
                raise PermissionDenied
            from .admin_interactions import interaction_reading
            return interaction_reading(request, obj, self)
        return super().change_view(request, object_id, form_url, extra_context)
