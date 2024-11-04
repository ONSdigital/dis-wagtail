from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from cms.core.models import ContactDetails


@hooks.register("register_icons")
def register_icons(icons: list[str]) -> list[str]:
    """Registers custom icons.

    Sources:
    - https://service-manual.ons.gov.uk/brand-guidelines/iconography/icon-set
    """
    return [
        *icons,
        "data-analysis.svg",
        "identity.svg",
        "news.svg",
    ]


class ContactDetailsViewSet(SnippetViewSet):
    """A snippet viewset for ContactDetails.

    See:
     - https://docs.wagtail.org/en/stable/topics/snippets/registering.html
     - https://docs.wagtail.org/en/stable/topics/snippets/customizing.html#icon
    """

    model = ContactDetails
    icon = "identity"


register_snippet(ContactDetailsViewSet)
