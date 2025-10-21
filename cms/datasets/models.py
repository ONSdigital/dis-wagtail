import logging
from collections.abc import Iterable, Mapping
from http import HTTPStatus
from typing import ClassVar

import requests
from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from queryish.rest import APIModel, APIQuerySet

from cms.datasets.utils import convert_old_dataset_format

logger = logging.getLogger(__name__)


# TODO: This needs a revisit. Consider caching + fewer requests
class ONSDatasetApiQuerySet(APIQuerySet):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.token: str | None = None

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
        published = response.get("published", True)
        # Annotate results if unpublished datasets were fetched
        for item in results:
            item["published"] = published

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

        api_response: dict = response.json()
        if is_detail_request:
            api_response = self._process_detail_response(api_response)
        else:
            api_response["published"] = params.get("published", "").lower() != "false"

        # The dataset API returns the per page count as "count" and the total results as "total_count"
        # Queryish expects "count" to be the total results count, so override it here
        if count := api_response.get("total_count"):
            api_response["count"] = count

        return api_response

    def _process_detail_response(self, response: dict) -> dict:
        # For detail responses, we may need to adjust the structure.
        # This only applies to the detail URL which currently uses the old format.
        if response.get("current"):
            # If it's a versioned dataset response using the old format, convert to new format
            dataset_data = convert_old_dataset_format(response["current"])
            # Store the next version info if available (this becomes our unpublished version)
            next_entry = response.get("next")
            dataset_data["next"] = convert_old_dataset_format(next_entry) if next_entry else {}
            return dataset_data
        return response


class ONSDataset(APIModel):
    base_query_class = ONSDatasetApiQuerySet

    search_fields: ClassVar[list[str]] = ["title", "version", "formatted_edition"]

    class Meta:
        base_url: str = settings.DATASETS_API_EDITIONS_URL
        detail_url: str = f"{settings.DATASETS_API_BASE_URL}/%s"
        fields: ClassVar = ["id", "description", "title", "version", "edition", "published", "next"]
        pagination_style = "offset-limit"
        verbose_name_plural = "ONS Datasets"

    @classmethod
    def from_query_data(cls, data: Mapping) -> "ONSDataset":
        # Handle new /v1/dataset-editions response structure
        dataset_id = data.get("dataset_id", data.get("id", ""))
        title = data.get("title") or "Title not provided"
        description = data.get("description") or "Description not provided"
        edition = data.get("edition", "")
        published = data.get("published", True)
        # Handle next (unpublished) version if present
        next_dataset_entry = data.get("next")

        if next_dataset_entry:
            # Recursively create ONSDataset for the unpublished version
            next_dataset_entry = ONSDataset.from_query_data(next_dataset_entry)

        # Extract version from latest_version object
        latest_version = data.get("latest_version", {})
        version_id = latest_version.get("id", "1") if isinstance(latest_version, dict) else "1"

        return cls(
            id=dataset_id,
            title=title,
            description=description,
            version=version_id,
            edition=edition,
            published=published,
            next=next_dataset_entry,
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
    def website_url(self) -> str:
        return f"{settings.ONS_WEBSITE_BASE_URL}{self.url_path}"
