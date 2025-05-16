from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from wagtail.admin.ui.tables import Column
from wagtail.coreutils import get_locales_display_names
from wagtail.models import Locale

if TYPE_CHECKING:
    from django.db.models import Model


# TODO: remove when upgrading to Wagtail 7.0
class LocaleColumn(Column):
    """Represents a Locale label."""

    cell_template_name = "wagtailadmin/tables/locale_cell.html"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            "locale_id",
            label=kwargs.pop("label", "Locale"),
            sort_key=kwargs.pop("sort_key", "locale"),
            classname=kwargs.pop("classname", "w-text-16"),
            **kwargs,
        )

    def get_cell_context_data(self, instance: "Model", parent_context: Mapping[str, Any]) -> dict[str, Any]:
        context: dict[str, Any] = super().get_cell_context_data(instance, parent_context)
        value = self.get_value(instance)
        if isinstance(value, int):
            value = get_locales_display_names().get(value)
        elif isinstance(value, Locale):
            value = value.get_display_name()
        context["value"] = value
        return context
