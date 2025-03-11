from typing import TYPE_CHECKING

from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.functional import cached_property
from wagtail.admin.forms.choosers import BaseFilterForm, SearchFilterMixin
from wagtail.admin.ui.tables import Column, DateColumn, StatusTagColumn
from wagtail.admin.utils import get_user_display_name
from wagtail.admin.views.generic.chooser import ChooseResultsView, ChooseView
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.users.views.users import UserColumn, get_users_filter_query

from .models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet


class UserFilterForm(SearchFilterMixin, BaseFilterForm):
    @cached_property
    def model_fields(self) -> set[str]:
        return {f.name for f in User._meta.get_fields()}

    def filter(self, objects: "QuerySet[User]") -> "QuerySet[User]":
        if search_query := self.cleaned_data.get("q"):
            conditions = get_users_filter_query(search_query, self.model_fields)
            return objects.filter(conditions)
        return objects


class UserChooserMixin:
    filter_form_class = UserFilterForm

    @property
    def columns(self) -> list[Column]:
        title_column = self.title_column  # type: ignore[attr-defined]
        title_column.label = "Name"

        return [
            UserColumn(
                "name",
                accessor=lambda u: get_user_display_name(u),  # pylint: disable=unnecessary-lambda
                label="Name",
                get_url=(
                    lambda obj: self.append_preserved_url_parameters(  # type: ignore[attr-defined]
                        reverse(self.chosen_url_name, args=(quote(obj.pk),))  # type: ignore[attr-defined]
                    )
                ),
                link_attrs={"data-chooser-modal-choice": True},
            ),
            Column(
                User.USERNAME_FIELD,
                accessor="get_username",
                label="Username",
                width="20%",
            ),
            StatusTagColumn(
                "is_active",
                accessor=lambda u: "Active" if u.is_active else "Inactive",
                primary=lambda u: u.is_active,
                label="Status",
                width="10%",
            ),
            DateColumn(
                "last_login",
                label="Last login",
                width="15%",
            ),
        ]


class UserChooseView(UserChooserMixin, ChooseView): ...


class UserChooseResultsView(UserChooserMixin, ChooseResultsView): ...


class UserChooserViewSet(ChooserViewSet):
    model = User
    icon = "user"
    choose_view_class = UserChooseView
    choose_results_view_class = UserChooseResultsView
    choose_one_text = "Choose a user"
    choose_another_text = "Choose another user"
    edit_item_text = "Edit this user"


user_chooser_viewset = UserChooserViewSet("user_chooser")
