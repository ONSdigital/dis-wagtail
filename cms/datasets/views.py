import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import DEFAULT_DB_ALIAS
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
from cms.datasets.permissions import user_can_access_unpublished_datasets
from cms.datasets.utils import deconstruct_chooser_dataset_compound_id, get_dataset_for_published_state

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


def _update_dataset_metadata(dataset: Dataset, *, title: str, description: str) -> list[str]:
    """Apply API metadata to a Dataset instance and return the updated field names.

    Args:
        dataset: The Dataset instance to update
        title: The new title from the API
        description: The new description from the API

    Returns:
        List of field names that were updated
    """
    updated_fields: list[str] = []
    if title and dataset.title != title:
        dataset.title = title
        updated_fields.append("title")
    if description and dataset.description != description:
        dataset.description = description
        updated_fields.append("description")
    return updated_fields


class DatasetChooserPermissionMixin:
    """Mixin to check permissions for accessing unpublished datasets."""

    def dispatch(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> "HttpResponse":
        # Check if requesting unpublished datasets
        is_published = request.GET.get("published", "").lower() == "true"

        if not is_published and not user_can_access_unpublished_datasets(request.user):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc,no-any-return]


class DatasetRetrievalMixin:
    """Mixin to retrieve dataset details from the API."""

    def retrieve_dataset(self, *, dataset_id: str, published: bool, access_token: str | None) -> ONSDataset:
        if not published and not user_can_access_unpublished_datasets(self.request.user):  # type: ignore[attr-defined]
            raise PermissionDenied
        # We fetch the dataset from the API to get the title and description
        queryset = ONSDataset.objects  # pylint: disable=no-member
        if access_token:
            queryset = queryset.with_token(access_token)
        item_from_api = queryset.get(pk=dataset_id)

        return get_dataset_for_published_state(item_from_api, published)


class DatasetBaseChooseViewMixin:
    @property
    def columns(self):  # type: ignore
        return [
            *getattr(super(), "columns", []),
            Column("edition", label="Edition", accessor="formatted_edition"),
            Column("version", label="Version", accessor="version"),
        ]


class DatasetSearchFilterForm(BaseFilterForm):
    q = forms.CharField(
        label="Search datasets",
        widget=forms.TextInput(attrs={"placeholder": "Dataset title"}),
        required=False,
    )
    published = forms.ChoiceField(
        label="Published status",
        choices=[
            ("false", "Unpublished"),
            ("true", "Published"),
        ],
        initial="false",
        required=False,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Hide the published filter when selecting datasets for a bundle
        if self.data.get("for_bundle") == "true":
            self.fields["published"].widget = forms.HiddenInput()

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

    def request_is_for_bundle(self) -> bool:
        """Check if the request is for selecting datasets for a bundle."""
        for_bundle_value: str = self.request.GET.get("for_bundle", "false")
        return for_bundle_value.lower() == "true"

    def get_object_list(self) -> Iterable[ONSDataset]:
        """Get the list of datasets with auth token and published filter."""
        # Get the auth token from the request
        access_token = self.request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)

        # Check if this is for a bundle - if so, force published=false as bundles
        # only allow unpublished datasets to be selected
        for_bundle = self.request_is_for_bundle()

        # Get the published filter value from GET params or form
        published = "false" if for_bundle else self.request.GET.get("published", "false")

        # Log audit event when accessing unpublished datasets
        if published == "false":
            logger.info("Unpublished datasets requested", extra={"username": self.request.user.username})

        # Build the queryset with token and published filter
        queryset = ONSDataset.objects.filter(published=published)  # pylint: disable=no-member

        if access_token:
            queryset = queryset.with_token(access_token)
        return queryset.all()  # type: ignore[no-any-return]

    def render_to_response(self) -> None:
        # This base class should not be used directly
        raise NotImplementedError()


class CustomChooseView(ChooseViewMixin, CreationFormMixin, ONSDatasetBaseChooseView): ...


class CustomChooseResultView(ChooseResultsViewMixin, CreationFormMixin, ONSDatasetBaseChooseView): ...


class DatasetChooseView(DatasetChooserPermissionMixin, DatasetBaseChooseViewMixin, CustomChooseView): ...


class DatasetChooseResultsView(DatasetChooserPermissionMixin, DatasetBaseChooseViewMixin, CustomChooseResultView): ...


class DatasetChosenView(ChosenViewMixin, ChosenResponseMixin, DatasetRetrievalMixin, View):
    def get_object(self, pk: Any) -> Dataset:
        # get_object is called before get_chosen_response_data
        # and self.model_class is Dataset, so we get or create the Dataset from ONSDatasets here
        # create the dataset object from the API response

        # The provided PK is actually a combination of dataset_id, edition and version
        dataset_id, edition, version, published = deconstruct_chooser_dataset_compound_id(str(pk))

        # Get the auth token from the request
        access_token = self.request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)

        item_from_api = self.retrieve_dataset(dataset_id=dataset_id, published=published, access_token=access_token)

        dataset, created = Dataset.objects.get_or_create(
            namespace=dataset_id,
            edition=edition,
            version=int(version),
            defaults={
                # Use title and description from the API, the rest was grabbed from the compound ID
                "title": item_from_api.title,
                "description": item_from_api.description,
            },
        )
        if not created:
            # Dataset already existed, check if metadata needs updating
            updated_fields = _update_dataset_metadata(
                dataset,
                title=item_from_api.title,
                description=item_from_api.description,
            )
            if updated_fields:
                dataset.save(update_fields=updated_fields)

        return dataset


class DatasetChosenMultipleViewMixin(ChosenMultipleViewMixin, DatasetRetrievalMixin):
    def get_objects(self, pks: list[Any]) -> QuerySet[Dataset]:  # pylint: disable=too-many-locals
        if not pks:
            return Dataset.objects.none()

        api_data_for_datasets: list[dict] = []

        # List of tuples (namespace, edition, version) for querying existing datasets
        lookup_criteria: list[tuple[str, str, int]] = []

        # Get the auth token from the request
        access_token = self.request.COOKIES.get(settings.ACCESS_TOKEN_COOKIE_NAME)

        # TODO: update when we can fetch items in bulk from the dataset API or use the cached listing view?
        for pk in pks:
            # The provided PK is actually a combination of dataset_id, edition and version
            dataset_id, edition, version, published = deconstruct_chooser_dataset_compound_id(str(pk))

            item_from_api = self.retrieve_dataset(dataset_id=dataset_id, published=published, access_token=access_token)

            # Use title and description from the API, the rest was grabbed from the compound ID
            version_int = int(version)
            api_data_for_datasets.append(
                {
                    "id": dataset_id,
                    "title": item_from_api.title,
                    "description": item_from_api.description,
                    "edition": edition,
                    "version": version_int,
                }
            )
            lookup_criteria.append((dataset_id, edition, version_int))

        existing_query = Q()
        for namespace, edition, ver in lookup_criteria:
            existing_query |= Q(namespace=namespace, edition=edition, version=ver)

        existing_datasets_map: dict[tuple[str, str, int], Dataset] = {
            (ds.namespace, ds.edition, ds.version): ds for ds in Dataset.objects.filter(existing_query)
        }

        datasets_to_create: list[Dataset] = []
        datasets_to_update: list[Dataset] = []
        for data in api_data_for_datasets:
            key = (data["id"], data["edition"], data["version"])
            existing_dataset = existing_datasets_map.get(key)

            if existing_dataset is None:
                # Dataset doesn't exist, create it
                datasets_to_create.append(
                    Dataset(
                        namespace=data["id"],
                        edition=data["edition"],
                        version=data["version"],
                        title=data["title"],
                        description=data["description"],
                    )
                )
            else:
                # Dataset exists, check if metadata needs updating
                updated_fields = _update_dataset_metadata(
                    existing_dataset,
                    title=data["title"],
                    description=data["description"],
                )
                if updated_fields:
                    datasets_to_update.append(existing_dataset)

        if datasets_to_create:
            Dataset.objects.bulk_create(datasets_to_create)
        if datasets_to_update:
            Dataset.objects.bulk_update(datasets_to_update, ["title", "description"])

        # Return the existing and newly created datasets, using the DEFAULT_DB_ALIAS to ensure we read from the default
        # database instance, as the newly created datasets may not yet be replicated to read replicas.
        return Dataset.objects.using(DEFAULT_DB_ALIAS).filter(existing_query)


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
