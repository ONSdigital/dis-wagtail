from typing import TYPE_CHECKING

import jinja2
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from wagtail.models import Page


# Breadcrumbs
@jinja2.pass_context
def breadcrumbs(context: jinja2.runtime.Context, page: "Page") -> list[dict[str, object]]:
    """Returns the breadcrumbs as a list of dictionaries for the given page."""
    breadcrumbs_list = []
    page_depth = 2
    for ancestor_page in page.get_ancestors().specific().defer_streamfields():
        if not ancestor_page.is_root():
            if ancestor_page.depth <= page_depth:
                breadcrumbs_list.append({"url": "/", "text": _("Home")})
            elif not getattr(ancestor_page, "exclude_from_breadcrumbs", False):
                breadcrumbs_list.append(
                    {"url": ancestor_page.get_url(request=context.get("request")), "text": ancestor_page.title}
                )
    return breadcrumbs_list
