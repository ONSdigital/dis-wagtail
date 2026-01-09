from typing import TYPE_CHECKING

from wagtail.admin.panels import FieldPanel

if TYPE_CHECKING:
    from laces.typing import RenderContext


class HeadlineFiguresFieldPanel(FieldPanel):
    class BoundPanel(FieldPanel.BoundPanel):
        template_name = "wagtailadmin/panels/headline_figures/figures_used_by_ancestor_data.html"

        def get_context_data(self, parent_context: RenderContext | None = None) -> RenderContext | None:
            context = super().get_context_data(parent_context)
            context["figures_used_by_ancestor"] = self.instance.figures_used_by_ancestor
            return context
