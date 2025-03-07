from django import forms
from django.views import View
from wagtail.admin.forms.choosers import BaseFilterForm
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.generic.chooser import (
    BaseChooseView,
    ChooseResultsViewMixin,
    ChooseViewMixin,
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
            Column("version", label="Version", accessor="version"),
        ]


class CustomSearchFilterMixin(forms.Form):
    q = forms.CharField(
        label="Search datasets",
        widget=forms.TextInput(attrs={"placeholder": "Dataset title"}),
        required=False,
    )

    def filter(self, objects):
        objects = super().filter(objects)
        search_query = self.cleaned_data.get("q")
        if search_query:
            search_query_lower = search_query.strip().lower()
            # This is brittle, as it doesn't use dynamically set search fields
            objects = [
                obj
                for obj in objects
                if search_query_lower in obj.title.lower()
                or search_query_lower in obj.formatted_edition.lower()
                or search_query_lower in obj.version.lower()
            ]
            self.is_searching = True
            self.search_query = search_query
        return objects


class CustomFilterForm(CustomSearchFilterMixin, BaseFilterForm): ...


class ONSDatasetBaseChooseView(BaseChooseView):
    model_class = ONSDataset
    filter_form_class = CustomFilterForm

    def get_object_list(self):
        # Due to pagination this is required for search to check entire list
        # The hardcoded limit will need changing.
        return self.model_class.objects.filter(limit=1000)  # pylint: disable=no-member

    def render_to_response(self):
        raise NotImplementedError()


class CustomChooseView(ChooseViewMixin, CreationFormMixin, ONSDatasetBaseChooseView): ...


class CustomChooseResultView(ChooseResultsViewMixin, CreationFormMixin, ONSDatasetBaseChooseView): ...


class DatasetChooseView(DatasetBaseChooseViewMixin, CustomChooseView): ...


class DatasetChooseResultsView(DatasetBaseChooseViewMixin, CustomChooseResultView): ...


class DatasetChosenView(ChosenViewMixin, ChosenResponseMixin, View):
    def get_object(self, pk):
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
                "url": item.url,
            },
        )
        return dataset


class DatasetChooserViewSet(ChooserViewSet):
    model = Dataset
    icon = "tag"
    choose_one_text = "Choose a dataset"
    choose_another_text = "Choose another dataset"
    choose_view_class = DatasetChooseView
    choose_results_view_class = DatasetChooseResultsView
    chosen_view_class = DatasetChosenView


dataset_chooser_viewset = DatasetChooserViewSet("dataset_chooser")
