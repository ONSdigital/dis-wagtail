from typing import Any

from wagtail.admin.action_menu import ActionMenuItem
from wagtail.admin.action_menu import SubmitForModerationMenuItem as CoreSubmitForModerationMenuItem


class UnlockWorkflowMenuItem(ActionMenuItem):
    item_url: str = ""

    def __init__(self, name: str, label: str, *args: Any, **kwargs: Any) -> None:
        self.name = name
        self.label = label
        self.icon_name = kwargs.pop("icon_name", "")
        self.item_url = kwargs.pop("item_url", "")

        super().__init__(*args, **kwargs)

    def get_url(self, parent_context: Any) -> str:
        return self.item_url


class SubmitForModerationMenuItem(CoreSubmitForModerationMenuItem):
    def get_context_data(self, parent_context: dict) -> dict:
        context = super().get_context_data(parent_context)

        # update the resubmit label so it doesn't include the workflow name.
        if context["label"].startswith("Resubmit to"):
            context["label"] = "Resubmit for review"

        return context
