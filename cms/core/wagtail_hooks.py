from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.snippets.models import register_snippet

from cms.core.models.snippets import GlossaryTerm
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


@hooks.register("after_create_snippet")
@hooks.register("after_edit_snippet")
def set_glossary_term_updated_by_to_current_user_after_create_and_edit(request, instance):
    """Automatically set the last updating user on Glossary Term on creation and modification."""
    if instance(instance, GlossaryTerm):
        instance.updated_by = request.user
        instance.save()


register_snippet(ContactDetailsViewSet)
register_snippet(GlossaryViewSet)
