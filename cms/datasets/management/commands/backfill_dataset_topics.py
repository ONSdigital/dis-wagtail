import logging
import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand

from cms.core.db_router import force_write_db
from cms.datasets.models import Dataset, ONSDataset
from cms.datasets.utils import get_local_topic_ids

if TYPE_CHECKING:
    from django.core.management.base import CommandParser

logger = logging.getLogger(__name__)

ACCESS_TOKEN_VAR_NAME = "DATASET_API_ACCESS_TOKEN"  # noqa: S105
BULK_UPDATE_BATCH_SIZE = 100


class Command(BaseCommand):
    """Backfill topics for locally stored datasets that are missing them."""

    help = (
        "Best-effort backfill of topic for locally stored datasets that are missing them. "
        "Datasets that cannot be looked up or have a topic we can't resolve are left untouched. "
        f"Unpublished datasets require an access token, given via --access-token or {ACCESS_TOKEN_VAR_NAME} env var."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run", action="store_true", dest="dry_run", default=False, help="Dry run -- don't change anything"
        )
        parser.add_argument(
            "--namespace",
            action="append",
            dest="namespace",
            metavar="NAMESPACE",
            help="Only backfill datasets in the given namespace (can be specified multiple times)",
        )
        parser.add_argument(
            "--access-token",
            dest="access_token",
            default=None,
            help=(
                "Access token for the dataset API, required for unpublished datasets. "
                f"Defaults to the {ACCESS_TOKEN_VAR_NAME} environment variable."
            ),
        )

    @force_write_db()
    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]
        if dry_run:
            logger.info("This is a dry run, no changes will be made.")

        datasets_by_namespace = self._get_datasets_missing_a_topic(options["namespace"])
        if not datasets_by_namespace:
            logger.info("No datasets missing a topic found.")
            return

        dataset_count = sum(len(datasets) for datasets in datasets_by_namespace.values())
        logger.info("Found %d datasets missing a topic, grouped by namespace:", dataset_count)

        topic_ids_by_namespace, unresolved = self._fetch_topic_ids(
            datasets_by_namespace, access_token=options["access_token"] or os.environ.get(ACCESS_TOKEN_VAR_NAME)
        )

        local_topic_ids = get_local_topic_ids(topic_ids_by_namespace.values())

        datasets_to_update: list[Dataset] = []
        for namespace, topic_id in topic_ids_by_namespace.items():
            if topic_id not in local_topic_ids:
                unresolved["topic not in the local taxonomy"].append(namespace)
                continue
            for dataset in datasets_by_namespace[namespace]:
                dataset.topic_id = topic_id
                datasets_to_update.append(dataset)

        self._apply_updates(datasets_to_update, dry_run=dry_run)
        self._report_unresolved(unresolved)

    def _get_datasets_missing_a_topic(self, namespaces: list[str] | None) -> dict[str, list[Dataset]]:
        """Return a dict of datasets missing a topic, grouped by namespace."""
        datasets_by_namespace = defaultdict(list)
        queryset = Dataset.objects.filter(topic__isnull=True)
        if namespaces:
            queryset = queryset.filter(namespace__in=namespaces)
        for dataset in queryset:
            datasets_by_namespace[dataset.namespace].append(dataset)
        return datasets_by_namespace

    def _fetch_topic_ids(
        self, datasets_by_namespace: dict[str, list[Dataset]], *, access_token: str | None
    ) -> tuple[dict[str, str], dict[str, list[str]]]:
        """Fetch primary topic ID per namespace in the API."""
        queryset = ONSDataset.objects  # pylint: disable=no-member
        if access_token:
            queryset = queryset.with_token(access_token)

        topic_ids_by_namespace: dict[str, str] = {}
        unresolved: dict[str, list[str]] = defaultdict(list)

        for namespace in datasets_by_namespace:
            try:
                api_dataset = queryset.get(pk=namespace)
                topic_id = self._get_primary_topic_id(api_dataset)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Failed to fetch dataset topic for backfill", extra={"namespace": namespace})
                unresolved["could not be looked up in dataset API"].append(namespace)
                continue

            if not topic_id:
                unresolved["no topic returned by the datet API"].append(namespace)
                continue

            topic_ids_by_namespace[namespace] = topic_id

        return topic_ids_by_namespace, unresolved

    @staticmethod
    def _get_primary_topic_id(api_dataset: ONSDataset) -> str | None:
        """Return the primary topic ID for a dataset, or None if it cannot be determined."""
        if topic_id := api_dataset.primary_topic_id:
            return topic_id
        if next_version := api_dataset.next:
            primary_topic_id: str | None = next_version.primary_topic_id
            return primary_topic_id
        return None

    def _apply_updates(self, datasets_to_update: list[Dataset], *, dry_run: bool) -> None:
        if not datasets_to_update:
            logger.info("No dataset topics could be resolved")
            return

        if dry_run:
            logger.info("Would have backfilled topic for %d datasets", len(datasets_to_update))
            for dataset in datasets_to_update:
                logger.info("\t%s -> %s", dataset.compound_id, dataset.topic_id)
            return

        Dataset.objects.bulk_update(datasets_to_update, ["topic"], batch_size=BULK_UPDATE_BATCH_SIZE)
        logger.info(
            "Backfilled dataset topics",
            extra={"count": len(datasets_to_update), "dataset_ids": [dataset.pk for dataset in datasets_to_update]},
        )

    def _report_unresolved(self, unresolved: dict[str, list[str]]) -> None:
        for reason, namespaces in unresolved.items():
            logger.warning("skipped %d namespaces for reason %s: %s", len(namespaces), reason, ", ".join(namespaces))
