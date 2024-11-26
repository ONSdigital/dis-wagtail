from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.urls import resolve
from wagtail.models import Page


class ParentIdentifyingChooserViewMixin:
    """A mixin that uses the 'parent_url' query parameter to attempt to identify
    a 'parent' for new objects, and add the values to the creation form.
    """

    def get_parent_object_initial_data(self) -> dict[str, Any]:
        """Attempt to identify the parent object from the 'parent_url' query parameter."""
        from_url = self.request.GET.get("from_url")
        if not from_url:
            return {}

        resolved_url = resolve(from_url)
        if resolved_url.view_name == "wagtailadmin_pages:add":
            try:
                content_type = ContentType.objects.get_by_natural_key(resolved_url.kwargs["content_type_app_name"], resolved_url.kwargs["content_type_model_name"])
            except ContentType.DoesNotExist:
                return {}
            return {
                "parent_object_content_type": content_type,
                "parent_object_id_outstanding": True,
            }

        if resolved_url.view_name == "wagtailadmin_pages:edit":
            try:
                page = Page.objects.get(id=resolved_url.kwargs["page_id"])
            except Page.DoesNotExist:
                return {}
            return {
                "parent_object_content_type": page.cached_content_type,
                "parent_object_id": resolved_url.kwargs["page_id"],
            }

        if resolved_url.view_name.startswith("wagtailsnippets_"):
            _, app_label, model_name = resolved_url.namespace.split("_")
            try:
                content_type = ContentType.objects.get_by_natural_key(app_label, model_name)
            except ContentType.DoesNotExist:
                return {}
            if resolved_url.url_name == "add":
                return {
                    "parent_object_content_type": content_type,
                    "parent_object_id_outstanding": True,
                }
            elif resolved_url.url_name == "edit":
                return {
                    "parent_object_content_type": content_type,
                    "parent_object_id": int(resolved_url.kwargs["pk"]),
                }
        return {}

    def get_creation_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_creation_form_kwargs()
        kwargs["initial"] = self.get_parent_object_initial_data()
        return kwargs
