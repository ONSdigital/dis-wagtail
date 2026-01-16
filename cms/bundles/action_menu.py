from typing import TYPE_CHECKING, Any

from django.forms import Media
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from wagtail.admin.ui.components import Component

from cms.bundles.enums import BundleStatus

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.utils.safestring import SafeString
    from laces.typing import RenderContext

    from cms.bundles.models import Bundle


class ActionMenuItem(Component):
    """Defines an item in the actions drop-up on the bundles add/edit view.

    Inspired by the core page/snippet ActionMenuItem.
    TODO: Revisit once https://github.com/wagtail/wagtail/issues/12422 is fixed
    """

    order: int = 100  # default order index if one is not specified on init
    template_name: str = "bundles/wagtailadmin/action_menu/menu_item.html"

    label: str = ""
    label_progress: str = ""  # shown on click
    name: str | None = None
    classname: str = ""
    icon_name: str = ""
    use_shortcut: bool = False  # registers the cmd+s shortcut in the template

    def __init__(self, order: int | None = None) -> None:
        if order is not None:
            self.order = order

    def is_shown(self, _context: dict[str, Any]) -> bool:
        """Whether this action should be shown on this request.

        context = dictionary containing at least:
            'request' = the current request object
            'bundle' = optional, the bundle being edited
        """
        return False

    def get_context_data(self, parent_context: RenderContext | None = None) -> RenderContext | None:
        """Defines context for the template, overridable to use more data."""
        context = super().get_context_data(parent_context=parent_context) or {}
        context.update(
            {
                "label": self.label,
                "label_progress": self.label_progress,
                "use_shortcut": self.use_shortcut,
                "name": self.name,
                "classname": self.classname,
                "icon_name": self.icon_name,
                "request": parent_context.get("request") if parent_context else None,
                "bundle": parent_context.get("bundle") if parent_context else None,
            }
        )
        return context


class CreateMenuItem(ActionMenuItem):
    name = "action-create"
    icon_name = "draft"
    label = "Save as draft"
    label_progress = "Saving…"
    use_shortcut = True

    def is_shown(self, context: dict[str, Any]) -> bool:
        return context["bundle"] is None


class SaveAsDraftMenuItem(ActionMenuItem):
    name = "action-edit"
    icon_name = "draft"
    label = "Save as draft"
    label_progress = "Saving…"
    use_shortcut = True

    def is_shown(self, context: dict[str, Any]) -> bool:
        bundle = context["bundle"]
        return bundle is not None and bundle.status == BundleStatus.DRAFT


class SaveMenuItem(SaveAsDraftMenuItem):
    label = "Save"

    def is_shown(self, context: dict[str, Any]) -> bool:
        bundle = context["bundle"]
        return bundle is not None and bundle.status == BundleStatus.IN_REVIEW


class SaveToInPreviewMenuItem(ActionMenuItem):
    name = "action-save-to-preview"
    label = "Save to preview"
    label_progress = "Saving…"
    icon_name = "view"

    def is_shown(self, context: dict[str, Any]) -> bool:
        bundle = context["bundle"]
        return bundle is not None and bundle.status == BundleStatus.DRAFT


class ReturnToDraftMenuItem(ActionMenuItem):
    name = "action-return-to-draft"
    label = "Return to draft"
    label_progress = "Returning to draft…"
    icon_name = "draft"

    def is_shown(self, context: dict[str, Any]) -> bool:
        bundle = context["bundle"]
        return bundle is not None and bundle.status in [BundleStatus.IN_REVIEW, BundleStatus.APPROVED]


class ReturnToInPreviewMenuItem(ActionMenuItem):
    name = "action-return-to-preview"
    label = "Return to preview"
    label_progress = "Returning to preview…"
    icon_name = "view"

    def is_shown(self, context: dict[str, Any]) -> bool:
        bundle = context["bundle"]
        return bundle is not None and bundle.status == BundleStatus.APPROVED


class ApproveMenuItem(ActionMenuItem):
    name = "action-approve"
    label = "Approve"
    label_progress = "Approving…"
    icon_name = "check"

    def is_shown(self, context: dict[str, Any]) -> bool:
        bundle = context["bundle"]
        return bundle is not None and bundle.status == BundleStatus.IN_REVIEW


class ManualPublishMenuItem(ActionMenuItem):
    name = "action-publish"
    label = "Publish"
    label_progres = "Publishing…"
    icon_name = "upload"

    def is_shown(self, context: dict[str, Any]) -> bool:
        bundle = context["bundle"]
        return bundle is not None and bundle.can_be_manually_published


class BundleActionMenu:
    template = "wagtailadmin/shared/action_menu/menu.html"
    default_item: ActionMenuItem | None = None

    def __init__(self, request: HttpRequest, bundle: Bundle | None = None, **kwargs: dict[str, Any]) -> None:
        self.request = request
        context: dict[str, Any] = kwargs
        context["request"] = request
        context["bundle"] = bundle
        self.context = context

        menu_items = [
            CreateMenuItem(order=0),
            SaveAsDraftMenuItem(order=1),
            SaveMenuItem(order=2),
            SaveToInPreviewMenuItem(order=10),
            ApproveMenuItem(order=20),
            ReturnToDraftMenuItem(order=30),
            ManualPublishMenuItem(order=40),
            ReturnToInPreviewMenuItem(order=50),
        ]

        self.menu_items = [menu_item for menu_item in menu_items if menu_item.is_shown(self.context)]

        self.menu_items.sort(key=lambda item: item.order)

        try:
            self.default_item = self.menu_items.pop(0)
        except IndexError:
            self.default_item = None

    def render_html(self) -> SafeString | str:
        if not self.default_item:
            return ""

        rendered_menu_items = [menu_item.render_html(self.context) for menu_item in self.menu_items]
        rendered_default_item = self.default_item.render_html(self.context)

        return render_to_string(
            self.template,
            {
                "default_menu_item": rendered_default_item,
                "show_menu": bool(self.menu_items),
                "rendered_menu_items": rendered_menu_items,
            },
            request=self.request,
        )

    @cached_property
    def media(self) -> Media:
        media = self.default_item.media if self.default_item else Media()
        for item in self.menu_items:
            media += item.media
        return media
