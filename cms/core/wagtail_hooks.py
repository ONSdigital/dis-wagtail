from django.templatetags.static import static
from django.utils.html import format_html_join
from wagtail import hooks
from wagtail.snippets.models import register_snippet

from cms.core.viewsets import ContactDetailsViewSet


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
    ]


@hooks.register("insert_editor_js")
def editor_js():
    js_files = [
        "/js/richtext_toolbar_settings.js",
        "/js/editor_minimap_settings.js",
    ]
    return format_html_join("\n", '<script src="{}"></script>', ((static(filename),) for filename in js_files))


register_snippet(ContactDetailsViewSet)
