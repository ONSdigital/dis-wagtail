from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin import messages
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


@hooks.register("insert_global_admin_css")
def global_admin_css() -> str:
    return format_html('<link rel="stylesheet" href="{}">', static("css/admin.css"))


register_snippet(ContactDetailsViewSet)
register_snippet(GlossaryViewSet)


@hooks.register("after_edit_page")
def after_edit_page(request, page):
    if page.locale.language_code != settings.LANGUAGE_CODE:
        return

    # Check if proper translations of the page exist, which are not simple aliases
    proper_translations = [
        translation for translation in page.get_translations().only("alias_of") if not translation.alias_of
    ]
    if len(proper_translations) > 0:
        messages.warning(
            request, "A translated version of this page exists. If you make any changes, please make sure to update it."
        )
