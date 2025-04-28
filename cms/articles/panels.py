from typing import TYPE_CHECKING

from wagtail.admin.panels import Panel

if TYPE_CHECKING:
    from typing import Optional

    from laces.typing import RenderContext


class HeadlineFiguresDataPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtailadmin/panels/headline_figures/figures_used_by_ancestor_data.html"

        def get_context_data(self, parent_context: "Optional[RenderContext]" = None) -> "Optional[RenderContext]":
            context = super().get_context_data(parent_context)
            context["figures_used_by_ancestor"] = self.instance.figures_used_by_ancestor
            return context
