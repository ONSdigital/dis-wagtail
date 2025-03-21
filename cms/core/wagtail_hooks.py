from django.contrib.auth.models import Permission
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.snippets.models import register_snippet

from cms.core.viewsets import ContactDetailsViewSet, GlossaryViewSet


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
def editor_js() -> str:
    """Modify the default behavior of the Wagtail admin editor."""
    return format_html('<script src="{}"></script>', static("js/wagtail-editor-customisations.js"))


@hooks.register("register_permissions")
def register_topic_page_highlighted_articles_permission():
    app = "wagtailadmin"

    return Permission.objects.filter(content_type__app_label=app, codename="add_topic_page_highlighted_articles")


register_snippet(ContactDetailsViewSet)
register_snippet(GlossaryViewSet)
