import logging
from collections.abc import Iterable, Mapping
from http import HTTPStatus
from typing import ClassVar

import requests
from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from queryish.rest import APIModel, APIQuerySet

from cms.datasets.utils import (
    construct_chooser_dataset_compound_id,
    convert_old_dataset_format,
    get_published_from_state,
)

logger = logging.getLogger(__name__)


# TODO: This needs a revisit. Consider caching + fewer requests
class ONSDatasetApiQuerySet(APIQuerySet):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.token: str | None = None
        self.limit: int = settings.DATASETS_API_DEFAULT_PAGE_SIZE

    def with_token(self, token: str) -> "ONSDatasetApiQuerySet":
        """Return a cloned queryset with the given authentication token.

        We clone the queryset to ensure the method is stateless and doesn't mutate
        the original queryset. This allows chaining operations (e.g.,
        ONSDataset.objects.with_token(token).filter(...).all()) without affecting
        other code that may be using the same base queryset instance.

        Args:
            token: Bearer token for API authentication

        Returns:
            Cloned queryset with token attached
        """
        clone: ONSDatasetApiQuerySet = self.clone()
        clone.token = token
        return clone

    def get_results_from_response(self, response: Mapping) -> Iterable:
        results: Iterable = response["items"]

        return results

    def fetch_api_response(self, url: str | None = None, params: Mapping | None = None) -> dict:
        # Add Authorization header if token is set
        headers = dict(self.http_headers) if self.http_headers else {}
        if self.token:
            # Note: Don't prepend "Bearer " - it's already in the token
            headers["Authorization"] = self.token

        if url is None:
            url = self.base_url
        if params is None:
            params = {}

        is_detail_request = url.startswith(ONSDataset.Meta.detail_url.split("%s", maxsplit=1)[0])

        try:
            logger.debug("Fetching datasets from API", extra={"url": url, "params": params})
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                logger.warning("Rate limit exceeded when fetching datasets", extra={"url": url})
                raise
            # Check for 5xx server errors (500-599)
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                logger.error(
                    "Server error when fetching datasets",
                    extra={"url": url, "status_code": e.response.status_code},
                )
                raise
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request failed when fetching datasets", extra={"url": url, "error": str(e)})
            raise

        try:
            api_response: dict = response.json()
        except ValueError as e:
            logger.error("Failed to parse JSON response when fetching datasets", extra={"url": url, "params": params})
            raise ValueError("Failed to parse JSON response from datasets API") from e

        # api_response should be a dict, let's raise a clear error if not
        if not isinstance(api_response, dict):
            logger.error("Invalid API response format when fetching datasets", extra={"url": url, "params": params})
            raise ValueError("Invalid API response format, expected a dictionary-like object")

        if is_detail_request:
            api_response = self._process_detail_response(api_response)

        # The dataset API returns the per page count as "count" and the total results as "total_count"
        # Queryish expects "count" to be the total results count, so override it here
        if count := api_response.get("total_count"):
            api_response["count"] = count

        return api_response

    @staticmethod
    def _process_detail_response(response: dict) -> dict:
        # For detail responses, we may need to adjust the structure.
        # This only applies to the detail URL which currently uses the old format.
        current = response.get("current")
        next_converted = convert_old_dataset_format(next_entry) if (next_entry := response.get("next")) else {}

        if current:
            dataset = convert_old_dataset_format(current)
            # Store the next version info if available (this becomes our unpublished version)
            dataset["next"] = next_converted
            return dataset

        if next_converted:
            # Return a minimal structure indicating no published version - this is necessary
            # if someone constructs a request for an unpublished version directly but indicating
            # they want the published one.
            return {"title": "No published version", "description": "", "next": next_converted}

        return response


class ONSDataset(APIModel):
    base_query_class = ONSDatasetApiQuerySet

    search_fields: ClassVar[list[str]] = ["title", "version", "formatted_edition"]

    class Meta:
        base_url: str = settings.DATASETS_API_EDITIONS_URL
        detail_url: str = f"{settings.DATASETS_API_BASE_URL}/%s"
        fields: ClassVar = ["id", "dataset_id", "description", "title", "version", "edition", "next"]
        pagination_style = "offset-limit"
        verbose_name_plural = "ONS Datasets"

    @classmethod
    def from_query_data(cls, data: Mapping) -> "ONSDataset":
        # Handle new /v1/dataset-editions response structure
        dataset_id = data.get("dataset_id", "id-not-provided")
        title = data.get("title") or "Title not provided"
        description = data.get("description") or "Description not provided"
        edition = data.get("edition", "edition-not-provided")
        next_version = data.get("next", {})
        published = get_published_from_state(data.get("state", "unknown"))

        if next_version:
            # Recursively create ONSDataset for the unpublished version
            next_version = ONSDataset.from_query_data(next_version)

        # Extract version from latest_version object
        latest_version = data.get("latest_version", {})
        version_id = latest_version.get("id", "1") if isinstance(latest_version, dict) else "1"

        return cls(
            # We construct the compound ID here. Note that we append the published state only as a
            # workaround so that the published state can be determined from the id alone.
            # This is necessary because we need to know which version to extract when using
            # the detail endpoint which returns "current" and "next" versions.
            id=construct_chooser_dataset_compound_id(
                dataset_id=dataset_id, edition=edition, version_id=version_id, published=published
            ),
            dataset_id=dataset_id,
            title=title,
            description=description,
            version=version_id,
            edition=edition,
            next=next_version,
        )

    @property
    def formatted_edition(self) -> str:
        edition: str = self.edition.replace("-", " ").title()  # pylint: disable=no-member
        return edition

    def __str__(self) -> str:
        title: str = self.title  # pylint: disable=no-member
        return title


class Dataset(models.Model):  # type: ignore[django-manager-missing]
    namespace = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    edition = models.CharField(max_length=255)
    version = models.IntegerField()

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            UniqueConstraint(fields=["namespace", "edition", "version"], name="dataset_id")
        ]

    def __str__(self) -> str:
        return f"{self.title} (Edition: {self.formatted_edition}, Ver: {self.version})"

    @property
    def formatted_edition(self) -> str:
        return self.edition.replace("-", " ").title()

    @property
    def url_path(self) -> str:
        """The path to the dataset landing page.
        Note that this may also direct to the latest version if the landing page doesn't exist.
        """
        return f"/datasets/{self.namespace}"

    @property
    def compound_id(self) -> str:
        """Return the compound ID for this local Dataset instance.

        Format: "<namespace>,<edition>,<version>"

        This identifier is used within the CMS for uniquely identifying datasets
        in the local database.

        Do not confuse this with the chooser dataset compound ID (see
        `construct_chooser_dataset_compound_id`), which includes an additional
        `published` flag used only for distinguishing API datasets (ONSDataset).
        """
        return f"{self.namespace},{self.edition},{self.version}"
