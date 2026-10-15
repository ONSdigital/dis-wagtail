from typing import TYPE_CHECKING

from wagtail.admin.action_menu import SubmitForModerationMenuItem as CoreSubmitForModerationMenuItem

if TYPE_CHECKING:
    from laces.typing import RenderContext


class SubmitForModerationMenuItem(CoreSubmitForModerationMenuItem):
    def get_context_data(self, parent_context: RenderContext | None) -> RenderContext | None:
        context = super().get_context_data(parent_context)

        # update the resubmit label so it doesn't include the workflow name.
        if context["label"].startswith("Resubmit to"):
            context["label"] = "Resubmit for review"

        return context
