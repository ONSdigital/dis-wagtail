from typing import Any

from wagtail.admin.action_menu import ActionMenuItem


class UnlockWorkflowMenuItem(ActionMenuItem):
    def __init__(self, name, label, *args: Any, **kwargs: Any) -> None:
        self.name = name
        self.label = label
        self.icon_name = kwargs.pop("icon_name", "")
        self.item_url = kwargs.pop("item_url", "")

        super().__init__(*args, **kwargs)

    def get_url(self, parent_context: Any) -> str:
        return self.item_url
