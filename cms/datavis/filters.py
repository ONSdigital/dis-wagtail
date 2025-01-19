from collections.abc import Sequence
from typing import ClassVar

from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _
from django_filters.filters import DateFromToRangeFilter
from wagtail.admin.filters import (
    DateRangePickerWidget,
    MultipleContentTypeFilter,
    WagtailFilterSet,
)

from cms.datavis.models import DataSource, Visualisation
from cms.datavis.utils import get_creatable_visualisation_content_types


class TrackedModelFilterSet(WagtailFilterSet):
    created_at = DateFromToRangeFilter(
        label=_("Created at"),
        widget=DateRangePickerWidget,
    )
    last_updated_at = DateFromToRangeFilter(
        label=_("Last updated at"),
        widget=DateRangePickerWidget,
    )


class VisualisationFilterSet(TrackedModelFilterSet):
    content_type = MultipleContentTypeFilter(
        label=_("Chart type"),
        queryset=lambda request: get_creatable_visualisation_content_types(),
        widget=CheckboxSelectMultiple,
    )

    class Meta:
        model = Visualisation
        fields: ClassVar[Sequence[str]] = ["collection", "content_type", "created_at", "created_by", "last_updated_at"]


class DataSourceFilterSet(TrackedModelFilterSet):
    class Meta:
        model = DataSource
        fields: ClassVar[Sequence[str]] = ["collection", "created_at", "created_by", "last_updated_at"]
