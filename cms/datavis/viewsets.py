from collections.abc import Sequence
from typing import Any, ClassVar

from django.urls import path
from wagtail.admin.panels import FieldPanel, ObjectList
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from cms.datavis.forms.datasource import DataSourceEditForm
from cms.datavis.models import DataSource, Visualisation
from cms.datavis.views.datasource import (
    DataSourceCopyView,
    DataSourceCreateView,
    DataSourceEditView,
    DataSourceHistoryView,
    DataSourceIndexView,
)
from cms.datavis.views.specific import (
    SpecificPreviewOnCreateView,
    SpecificPreviewOnEditView,
)
from cms.datavis.views.visualisation import (
    VisualisationCopyView,
    VisualisationCreateView,
    VisualisationDeleteView,
    VisualisationEditView,
    VisualisationHistoryView,
    VisualisationIndexView,
    VisualisationTypeSelectView,
)

from .filters import DataSourceFilterSet, VisualisationFilterSet


class DataSourceViewSet(SnippetViewSet):
    model = DataSource
    icon = "table-cells"
    base_form_class = DataSourceEditForm

    # Index config
    index_view_class = DataSourceIndexView
    filterset_class = DataSourceFilterSet
    list_display: ClassVar[Sequence[str]] = ["title", "column_count", "created_by", "created_at", "last_updated_at"]
    ordering: ClassVar[Sequence[Any]] = ["-last_updated_at"]

    # Other view overrides
    add_view_class = DataSourceCreateView
    copy_view_class = DataSourceCopyView
    edit_view_class = DataSourceEditView
    history_view_class = DataSourceHistoryView

    edit_handler = ObjectList(
        [
            FieldPanel("title"),
            FieldPanel("collection"),
            FieldPanel("csv_file"),
            FieldPanel("table"),
        ],
        base_form_class=DataSourceEditForm,
    )


class VisualisationViewSet(SnippetViewSet):
    icon = "chart-area"
    model = Visualisation

    # Index config
    index_view_class = VisualisationIndexView
    filterset_class = VisualisationFilterSet
    list_display: ClassVar[Sequence[str]] = [
        "name",
        "type_label",
        "created_by",
        "created_at",
        "last_updated_at",
    ]
    ordering: ClassVar[Sequence[Any]] = ["-last_updated_at"]

    # Other view overrides
    add_view_class = VisualisationTypeSelectView
    specific_add_view_class = VisualisationCreateView
    copy_view_class = VisualisationCopyView
    delete_view_class = VisualisationDeleteView
    edit_view_class = VisualisationEditView
    history_view_class = VisualisationHistoryView
    preview_on_add_view_class = SpecificPreviewOnCreateView
    preview_on_edit_view_class = SpecificPreviewOnEditView

    def get_urlpatterns(self) -> list[Any]:
        urlpatterns = [
            pattern
            for pattern in super().get_urlpatterns()
            if getattr(pattern, "name", "") not in ["preview_on_add", "preview_on_edit"]
        ]
        urlpatterns.extend(
            [
                path("new/<str:specific_type>/", self.specific_add_view, name="specific_add"),
                path(
                    "preview/<str:specific_type>/",
                    self.preview_on_add_view,
                    name="preview_on_add",
                ),
                path(
                    "preview/<str:specific_type>/<str:pk>/",
                    self.preview_on_edit_view,
                    name="preview_on_edit",
                ),
            ]
        )
        return urlpatterns

    def get_add_view_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        kwargs = super().get_add_view_kwargs(**kwargs)
        del kwargs["panel"]
        del kwargs["form_class"]
        return kwargs

    def get_edit_view_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        kwargs = super().get_edit_view_kwargs(**kwargs)
        del kwargs["panel"]
        del kwargs["form_class"]
        return kwargs

    @property
    def specific_add_view(self) -> "VisualisationCreateView":
        return self.construct_view(  # type: ignore[no-any-return]
            self.specific_add_view_class, **self.get_add_view_kwargs()
        )

    @property
    def preview_on_add_view(self) -> "SpecificPreviewOnCreateView":
        return self.construct_view(self.preview_on_add_view_class)  # type: ignore[no-any-return]

    @property
    def preview_on_edit_view(self) -> "SpecificPreviewOnEditView":
        return self.construct_view(self.preview_on_edit_view_class)  # type: ignore[no-any-return]


class DatavisViewSetGroup(SnippetViewSetGroup):
    menu_label = "Datavis"
    items: ClassVar[Sequence[type["SnippetViewSet"]]] = [DataSourceViewSet, VisualisationViewSet]
