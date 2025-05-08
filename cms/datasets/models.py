import logging
import re
from collections.abc import Iterable, Mapping
from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint
from queryish.rest import APIModel, APIQuerySet

logger = logging.getLogger(__name__)

EDITIONS_PATTERN = re.compile(r"/editions/([^/]+)/")
DATASETS_BASE_API_URL = f"{settings.ONS_API_BASE_URL}/datasets"


# TODO: This needs a revisit. Consider caching + fewer requests
class ONSDatasetApiQuerySet(APIQuerySet):
    def get_results_from_response(self, response: Mapping) -> Iterable:
        results: Iterable = response["items"]
        return results

    def fetch_api_response(self, url: str | None = None, params: Mapping | None = None) -> dict:
        api_response: dict = super().fetch_api_response(url=url, params=params)
        # The dataset API returns the per page count as "count" and the total results as "total_count"
        # Queryish expects "count" to be the total results count, so override it here
        if count := api_response.get("total_count"):
            api_response["count"] = count
        return api_response


class ONSDataset(APIModel):
    base_query_class = ONSDatasetApiQuerySet

    search_fields: ClassVar[list[str]] = ["title", "version", "formatted_edition"]

    class Meta:
        base_url: str = DATASETS_BASE_API_URL
        detail_url: str = f"{DATASETS_BASE_API_URL}/%s"
        fields: ClassVar = ["id", "description", "title", "version", "edition"]
        pagination_style = "offset-limit"
        verbose_name_plural = "ONS Datasets"

    @classmethod
    def from_query_data(cls, data: Mapping) -> "ONSDataset":
        url: str = data["links"]["latest_version"]["href"]
        edition_match = EDITIONS_PATTERN.search(url)
        if not edition_match:
            raise ValueError(f"Found invalid dataset URL, missing edition: {url} for dataset: {data['id']}")
        edition = edition_match.group(1)
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            version=data["links"]["latest_version"]["id"],
            edition=edition,
        )

    @property
    def formatted_edition(self) -> str:
        edition: str = self.edition.replace("-", " ").title()  # pylint: disable=no-member
        return edition

    def __str__(self) -> str:
        title: str = self.title  # pylint: disable=no-member
        return title


class Dataset(models.Model):
    namespace = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    version = models.CharField(max_length=255)
    edition = models.CharField(max_length=255)

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
        return f"/datasets/{self.namespace}"

    @property
    def website_url(self) -> str:
        return f"{settings.ONS_WEBSITE_BASE_URL}{self.url_path}"
