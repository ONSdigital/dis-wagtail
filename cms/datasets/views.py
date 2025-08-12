from collections.abc import Iterable
from typing import Any

from django import forms
from django.db.models import Q, QuerySet
from django.views import View
from wagtail.admin.forms.choosers import BaseFilterForm
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.generic.chooser import (
    BaseChooseView,
    ChooseResultsViewMixin,
    ChooseViewMixin,
    ChosenMultipleViewMixin,
    ChosenResponseMixin,
    ChosenViewMixin,
    CreationFormMixin,
)
from wagtail.admin.viewsets.chooser import ChooserViewSet

from cms.datasets.models import Dataset, ONSDataset


class DatasetBaseChooseViewMixin:
    @property
    def columns(self):  # type: ignore
        return [
            *getattr(super(), "columns", []),
            Column("edition", label="Edition", accessor="formatted_edition"),
            Column("version", label="Latest Version", accessor="version"),
        ]


class DatasetSearchFilterForm(BaseFilterForm):
    q = forms.CharField(
        label="Search datasets",
        widget=forms.TextInput(attrs={"placeholder": "Dataset title"}),
        required=False,
    )

    def filter(self, objects: Iterable[Any]) -> Iterable[Any]:
        objects = super().filter(objects)

        # This search filter implementation is required on our side as the API does not support filtering yet
        search_query = self.cleaned_data.get("q")
        if search_query:
            search_query_lower = search_query.strip().lower()
            objects = [obj for obj in objects if self.obj_matches_search_query(obj, search_query_lower)]
            self.is_searching = True
            self.search_query = search_query
        return objects

    @staticmethod
    def obj_matches_search_query(obj: Any, search_query_lower: str) -> bool:
        return any(search_query_lower in getattr(obj, search_field).lower() for search_field in obj.search_fields)


class ONSDatasetBaseChooseView(BaseChooseView):
    model_class = ONSDataset
    filter_form_class = DatasetSearchFilterForm

    def render_to_response(self) -> None:
        raise NotImplementedError()


class CustomChooseView(ChooseViewMixin, CreationFormMixin, ONSDatasetBaseChooseView): ...


class CustomChooseResultView(ChooseResultsViewMixin, CreationFormMixin, ONSDatasetBaseChooseView): ...


class DatasetChooseView(DatasetBaseChooseViewMixin, CustomChooseView): ...


class DatasetChooseResultsView(DatasetBaseChooseViewMixin, CustomChooseResultView): ...


class DatasetChosenView(ChosenViewMixin, ChosenResponseMixin, View):
    def get_object(self, pk: Any) -> Dataset:
        # get_object is called before get_chosen_response_data
        # and self.model_class is Dataset, so we get or create the Dataset from ONSDatasets here
        # create the dataset object from the API response
        item = ONSDataset.objects.get(pk=pk)  # pylint: disable=no-member
        dataset, _ = Dataset.objects.get_or_create(
            namespace=item.id,
            edition=item.edition,
            version=item.version,
            defaults={
                "title": item.title,
                "description": item.description,
            },
        )
        return dataset


class DatasetChosenMultipleViewMixin(ChosenMultipleViewMixin):
    def get_objects(self, pks: list[Any]) -> QuerySet[Dataset]:
        if not pks:
            return Dataset.objects.none()

        api_data_for_datasets: list[ONSDataset] = []

        # List of tuples (namespace, edition, version) for querying existing datasets
        lookup_criteria: list[tuple[str, str, str]] = []

        # TODO: update when we can fetch items in bulk from the dataset API or use the cached listing view?
        for pk in pks:
            item_from_api = ONSDataset.objects.get(pk=pk)  # pylint: disable=no-member

            api_data_for_datasets.append(item_from_api)
            lookup_criteria.append((item_from_api.id, item_from_api.edition, item_from_api.version))

        existing_query = Q()
        for namespace, edition, version in lookup_criteria:
            existing_query |= Q(namespace=namespace, edition=edition, version=version)

        existing_datasets_map: dict[tuple[str, str, int], Dataset] = {
            (ds.namespace, ds.edition, ds.version): ds for ds in Dataset.objects.filter(existing_query)
        }

        datasets_to_create_instances: list[Dataset] = []
        for data in api_data_for_datasets:
            key = (data.id, data.edition, data.version)
            if key not in existing_datasets_map:
                datasets_to_create_instances.append(
                    Dataset(
                        namespace=data.id,
                        edition=data.edition,
                        version=data.version,
                        title=data.title,
                        description=data.description,
                    )
                )

        if datasets_to_create_instances:
            Dataset.objects.bulk_create(datasets_to_create_instances)
        return Dataset.objects.filter(existing_query)


class DatasetChosenMultipleView(DatasetChosenMultipleViewMixin, ChosenResponseMixin, View): ...


class DatasetChooserViewSet(ChooserViewSet):
    model = Dataset
    icon = "tag"
    choose_one_text = "Choose a dataset"
    choose_another_text = "Choose another dataset"
    choose_view_class = DatasetChooseView
    choose_results_view_class = DatasetChooseResultsView
    chosen_view_class = DatasetChosenView
    chosen_multiple_view_class = DatasetChosenMultipleView


dataset_chooser_viewset = DatasetChooserViewSet("dataset_chooser")
