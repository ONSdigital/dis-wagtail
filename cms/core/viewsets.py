from typing import ClassVar

from django.utils.translation import gettext_lazy as _
from wagtail.admin.ui.tables import Column, UpdatedAtColumn
from wagtail.snippets.views.chooser import ChooseResultsView as SnippetChooseResultsView
from wagtail.snippets.views.chooser import ChooseView as SnippetChooseView
from wagtail.snippets.views.chooser import SnippetChooserViewSet
from wagtail.snippets.views.snippets import IndexView as SnippetIndexView
from wagtail.snippets.views.snippets import SnippetViewSet

from cms.core.models import ContactDetails


class ContactDetailsIndex(SnippetIndexView):
    list_display: ClassVar[list[str | Column]] = ["name", "email", "phone", UpdatedAtColumn()]


class ContactDetailsChooseColumnsMixin:
    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column
        title_column.label = _("Name")
        return [title_column, Column("email"), Column("phone")]  # type: ignore[attr-defined]


class ContactDetailsChooseView(ContactDetailsChooseColumnsMixin, SnippetChooseView): ...


class ContactDetailsChooseResultsView(ContactDetailsChooseColumnsMixin, SnippetChooseResultsView): ...


class ContactDetailsChooserViewset(SnippetChooserViewSet):
    choose_view_class = ContactDetailsChooseView
    choose_results_view_class = ContactDetailsChooseResultsView


class ContactDetailsViewSet(SnippetViewSet):
    """A snippet viewset for ContactDetails.

    See:
     - https://docs.wagtail.org/en/stable/topics/snippets/registering.html
     - https://docs.wagtail.org/en/stable/topics/snippets/customizing.html#icon
    """

    model = ContactDetails
    icon = "identity"

    index_view_class = ContactDetailsIndex
    chooser_viewset_class = ContactDetailsChooserViewset
