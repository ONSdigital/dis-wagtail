from typing import TYPE_CHECKING

from django.conf import settings
from wagtail.admin.panels import FieldPanel

if TYPE_CHECKING:
    from laces.typing import RenderContext


class ExclusiveTaxonomyFieldPanel(FieldPanel):
    class BoundPanel(FieldPanel.BoundPanel):
        template_name = "wagtailadmin/panels/exclusive_taxonomy/exclusive_taxonomy_panel.html"

        def get_context_data(self, parent_context: RenderContext | None = None) -> RenderContext | None:
            context = super().get_context_data(parent_context)

            # If the instance is not saved yet, we don't have any translations to check against.
            if not self.instance.pk:
                return context

            if self.instance.locale_id != self.instance.get_root().locale_id and (
                default_locale_page := self.instance.get_translations()
                .filter(locale__language_code=settings.LANGUAGE_CODE)
                .only("id", "topic")
                .first()
            ):
                context["forced_topic"] = default_locale_page.topic
                context["default_locale_page_id"] = default_locale_page.id
            return context
