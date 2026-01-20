from typing import ClassVar

from django.db.models import F, QuerySet
from wagtail.admin.ui.tables import Column, LocaleColumn, UpdatedAtColumn, UserColumn
from wagtail.snippets.views.chooser import ChooseResultsView as SnippetChooseResultsView
from wagtail.snippets.views.chooser import ChooseView as SnippetChooseView
from wagtail.snippets.views.chooser import SnippetChooserViewSet
from wagtail.snippets.views.snippets import IndexView as SnippetIndexView
from wagtail.snippets.views.snippets import SnippetViewSet

from cms.core.models import ContactDetails, Definition


class ContactDetailsIndex(SnippetIndexView):
    list_display: ClassVar[list[str | Column]] = ["name", "locale", "email", "phone", UpdatedAtColumn()]


class ContactDetailsChooseColumnsMixin:
    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.label = "Name"
        return [
            title_column,
            LocaleColumn(classname="w-text-16 w-w-[120px]"),  # w-w-[120px] is used to adjust the width
            Column("email"),
            Column("phone"),
        ]


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


class DefinitionsIndex(SnippetIndexView):
    list_display: ClassVar[list[str | Column]] = [
        "name",
        "locale",
        UpdatedAtColumn(),
        UserColumn("updated_by"),
        UserColumn("owner"),
    ]

    def get_base_queryset(self) -> QuerySet[Definition]:
        queryset: QuerySet[Definition] = super().get_base_queryset()
        return queryset.select_related("latest_revision__user", "latest_revision__user__wagtail_userprofile")


class DefinitionsChooseColumnsMixin:
    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.label = "Name"
        return [
            title_column,
            LocaleColumn(classname="w-text-16 w-w-[120px]"),  # w-w-[120px] is used to adjust the width
            UpdatedAtColumn(),
            UserColumn("updated_by"),
        ]

    def get_object_list(self) -> QuerySet[Definition]:
        queryset = Definition.objects.select_related(
            "latest_revision", "latest_revision__user", "latest_revision__user__wagtail_userprofile"
        )
        queryset = queryset.annotate(_updated_at=F("latest_revision__created_at"))
        return queryset


class DefinitionChooseView(DefinitionsChooseColumnsMixin, SnippetChooseView): ...


class DefinitionChooseResultsView(DefinitionsChooseColumnsMixin, SnippetChooseResultsView): ...


class DefinitionChooserViewSet(SnippetChooserViewSet):
    choose_view_class = DefinitionChooseView
    choose_results_view_class = DefinitionChooseResultsView


class DefinitionViewSet(SnippetViewSet):
    """A snippet viewset for Definitions."""

    model = Definition
    icon = "list-ul"

    index_view_class = DefinitionsIndex
    chooser_viewset_class = DefinitionChooserViewSet
