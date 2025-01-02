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


register_snippet(ContactDetailsViewSet)
