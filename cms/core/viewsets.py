from typing import ClassVar

from wagtail.admin.ui.tables import Column, UpdatedAtColumn, UserColumn
from wagtail.snippets.views.chooser import ChooseResultsView as SnippetChooseResultsView
from wagtail.snippets.views.chooser import ChooseView as SnippetChooseView
from wagtail.snippets.views.chooser import SnippetChooserViewSet
from wagtail.snippets.views.snippets import CreateView as SnippetCreateView
from wagtail.snippets.views.snippets import EditView as SnippetEditView
from wagtail.snippets.views.snippets import IndexView as SnippetIndexView
from wagtail.snippets.views.snippets import SnippetViewSet

from cms.core.models import ContactDetails, GlossaryTerm


class ContactDetailsIndex(SnippetIndexView):
    list_display: ClassVar[list[str | Column]] = ["name", "email", "phone", UpdatedAtColumn()]


class ContactDetailsChooseColumnsMixin:
    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.label = "Name"
        return [title_column, Column("email"), Column("phone")]


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


class GlossaryTermCreateView(SnippetCreateView):
    def save_instance(self) -> GlossaryTerm:
        """Automatically set the last updating user on Glossary Term on creation and modification."""
        instance: GlossaryTerm = super().save_instance()
        instance.updated_by = self.request.user
        instance.save(update_fields=["updated_by"])
        return instance


class GlossaryTermEditView(SnippetEditView):
    def save_instance(self) -> GlossaryTerm:
        """Automatically set the last updating user on Glossary Term on creation and modification."""
        instance: GlossaryTerm = super().save_instance()
        instance.updated_by = self.request.user
        instance.save(update_fields=["updated_by"])
        return instance


class GlossaryTermsIndex(SnippetIndexView):
    list_display: ClassVar[list[str | Column]] = [
        "name",
        UpdatedAtColumn(),
        UserColumn("updated_by"),
        UserColumn("owner"),
    ]


class GlossaryTermsChooseColumnsMixin:
    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.label = "Name"
        return [title_column, UpdatedAtColumn(), UserColumn("updated_by")]


class GlossaryChooseView(GlossaryTermsChooseColumnsMixin, SnippetChooseView): ...


class GlossaryChooseResultsView(GlossaryTermsChooseColumnsMixin, SnippetChooseResultsView): ...


class GlossaryChooserViewset(SnippetChooserViewSet):
    choose_view_class = GlossaryChooseView
    choose_results_view_class = GlossaryChooseResultsView


class GlossaryViewSet(SnippetViewSet):
    """A snippet viewset for Glossary."""

    model = GlossaryTerm
    icon = "list-ul"

    index_view_class = GlossaryTermsIndex
    chooser_viewset_class = GlossaryChooserViewset

    add_view_class = GlossaryTermCreateView
    edit_view_class = GlossaryTermEditView
