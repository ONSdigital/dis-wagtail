from typing import TYPE_CHECKING

from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from wagtail import hooks
from wagtail.admin import messages
from wagtail.admin.utils import get_valid_next_url_from_request
from wagtail.models import Page
from wagtail.snippets.models import register_snippet

from cms.core.utils import redirect
from cms.core.viewsets import ContactDetailsViewSet, DefinitionViewSet
from cms.release_calendar.models import ReleaseCalendarIndex, ReleaseCalendarPage

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.http import HttpRequest, HttpResponsePermanentRedirect, HttpResponseRedirect
    from wagtail.admin.views.bulk_action import BulkAction


@hooks.register("register_icons")
def register_icons(icons: list[str]) -> list[str]:
    """Registers custom icons.

    Sources:
    - https://service-manual.ons.gov.uk/brand-guidelines/iconography/icon-set
    """
    return [
        *icons,
        "boxes-stacked.svg",
        "data-analysis.svg",
        "identity.svg",
        "news.svg",
        "wagtailfontawesomesvg/solid/chart-bar.svg",
        "wagtailfontawesomesvg/solid/chart-column.svg",
        "wagtailfontawesomesvg/solid/chart-line.svg",
        "wagtailfontawesomesvg/solid/chart-area.svg",
        "wagtailfontawesomesvg/solid/table-cells.svg",
        "wagtailfontawesomesvg/solid/location-crosshairs.svg",
        "wagtailfontawesomesvg/solid/square.svg",
    ]


@hooks.register("insert_editor_js")
def editor_js() -> str:
    """Modify the default behavior of the Wagtail admin editor."""
    return format_html('<script src="{}"></script>', static("js/wagtail-editor-customisations.js"))


@hooks.register("insert_global_admin_css")
def global_admin_css() -> str:
    return format_html('<link rel="stylesheet" href="{}">', static("css/admin.css"))


register_snippet(ContactDetailsViewSet)
register_snippet(DefinitionViewSet)


_BLOCKED_TITLES_PREVIEW_COUNT = 5


def _page_blocks_deletion(page: Page) -> bool:
    """Return True if deleting this page should be blocked by the previously-published rule.

    Release Calendar pages are handled by `cms.release_calendar.wagtail_hooks` for the
    single-page flow, but the bulk-action flow bypasses `before_delete_page`, so this
    helper accounts for them too.
    """
    specific_class = page.specific_class
    if specific_class is ReleaseCalendarIndex:
        return True
    if specific_class is ReleaseCalendarPage:
        # Release Calendar pages have no subpages, so no descendant check is needed.
        if page.first_published_at is not None:
            return True
        return page.get_translations().filter(first_published_at__isnull=False).exists()
    if page.first_published_at is not None:
        return True
    if page.get_translations().filter(first_published_at__isnull=False).exists():
        return True
    has_previously_published_descendant: bool = page.get_descendants().filter(first_published_at__isnull=False).exists()
    return has_previously_published_descendant


@hooks.register("before_delete_page")
def prevent_delete_of_previously_published_page(
    request: HttpRequest, page: Page
) -> HttpResponseRedirect | HttpResponsePermanentRedirect | None:
    """Block deletion of any page that has ever been published.

    Release Calendar pages are handled by `cms.release_calendar.wagtail_hooks`.
    """
    if page.specific_class in (ReleaseCalendarPage, ReleaseCalendarIndex):
        return None

    if not _page_blocks_deletion(page):
        return None

    message = mark_safe(
        "<b>Deletion Not Allowed</b><br>This page cannot be deleted because it (or one of its descendants) has been "
        "published previously. Only pages that have never been published can be deleted."
    )

    messages.warning(
        request,
        message,
    )
    return redirect("wagtailadmin_pages:edit", page.pk, preserve_request=False)


@hooks.register("before_bulk_action")
def prevent_bulk_delete_of_previously_published_pages(
    request: HttpRequest,
    action_type: str,
    objects: Sequence[Page],
    action: BulkAction,  # pylint: disable=unused-argument
) -> HttpResponseRedirect | HttpResponsePermanentRedirect | None:
    """Block the Wagtail page-explorer bulk-delete action when any selected page (or any
    of its descendants) has been published previously. The per-page `before_delete_page`
    hook is bypassed by the bulk-action flow, so this guard covers that gap.
    """
    if action_type != "delete":
        return None
    if not objects or not all(isinstance(obj, Page) for obj in objects):
        # If some objects are not pages, return - this is a sanity check,
        # not expected to occur in normal operation.
        return None

    blocked_titles = [page.title for page in objects if _page_blocks_deletion(page)]
    if not blocked_titles:
        return None

    preview = ", ".join(f"'{title}'" for title in blocked_titles[:_BLOCKED_TITLES_PREVIEW_COUNT])
    if len(blocked_titles) > _BLOCKED_TITLES_PREVIEW_COUNT:
        preview += f", and {len(blocked_titles) - _BLOCKED_TITLES_PREVIEW_COUNT} more"

    message = format_html(
        "<b>Deletion Not Allowed</b><br>The following selected page(s) cannot be deleted because they (or their "
        "descendants or translations) have been published previously: {}. Only pages that have never been published "
        "can be deleted.",
        preview,
    )

    messages.warning(request, message)
    return redirect(get_valid_next_url_from_request(request) or reverse("wagtailadmin_home"), preserve_request=False)


@hooks.register("after_edit_page")
def after_edit_page(request: HttpRequest, page: Page) -> None:
    if page.locale.language_code != settings.LANGUAGE_CODE:
        return

    # Check if proper translations of the page exist, which are not simple aliases
    proper_translation = page.get_translations().filter(alias_of__isnull=True).only("id").first()
    if proper_translation:
        admin_edit_url = reverse("wagtailadmin_pages:edit", args=[proper_translation.id])
        messages.warning(
            request,
            "A translated version of this page exists. If you make any changes, please make sure to update it.",
            buttons=[
                messages.button(admin_edit_url, "Go to translation"),
            ],
            extra_tags="safe",
        )
