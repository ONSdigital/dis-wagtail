from typing import TYPE_CHECKING

from django.conf import settings
from wagtail.admin.panels import FieldPanel

if TYPE_CHECKING:
    from typing import Optional

    from laces.typing import RenderContext


class ExclusiveTaxonomyFieldPanel(FieldPanel):
    class BoundPanel(FieldPanel.BoundPanel):
        template_name = "wagtailadmin/panels/exclusive_taxonomy/exclusive_taxonomy_panel.html"

        def get_context_data(self, parent_context: "Optional[RenderContext]" = None) -> "Optional[RenderContext]":
            context = super().get_context_data(parent_context)

            if self.instance.locale != self.instance.get_root().locale and (
                english_page := self.instance.get_translations()
                .filter(locale__language_code=settings.LANGUAGE_CODE)
                .only("id", "topic")
                .first()
            ):
                context["forced_topic"] = english_page.topic
                context["english_page_id"] = english_page.id
            return context
