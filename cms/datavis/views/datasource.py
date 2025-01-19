from typing import TYPE_CHECKING

from wagtail.snippets.views.snippets import (
    CopyView,
    CreateView,
    EditView,
    HistoryView,
    IndexView,
)

from cms.datavis.models import DataSource

from .mixins import RemoveChecksSidePanelMixin, RemoveSnippetIndexBreadcrumbItemMixin

if TYPE_CHECKING:
    from django.db.models import QuerySet


class DataSourceIndexView(RemoveSnippetIndexBreadcrumbItemMixin, IndexView):
    def get_base_queryset(self) -> "QuerySet[DataSource]":
        """Overrides the default implementation to fetch creating users in the
        same query (avoiding n+1 queries).
        """
        return DataSource.objects.select_related("created_by")


class DataSourceCreateView(RemoveSnippetIndexBreadcrumbItemMixin, RemoveChecksSidePanelMixin, CreateView):
    pass


class DataSourceEditView(RemoveSnippetIndexBreadcrumbItemMixin, RemoveChecksSidePanelMixin, EditView):
    pass


class DataSourceCopyView(RemoveSnippetIndexBreadcrumbItemMixin, RemoveChecksSidePanelMixin, CopyView):
    pass


class DataSourceHistoryView(RemoveSnippetIndexBreadcrumbItemMixin, HistoryView):
    pass
