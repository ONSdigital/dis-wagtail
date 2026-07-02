import logging
from collections.abc import Iterable, Mapping
from typing import Any

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import BaseCommand

from cms.taxonomy.models import Topic

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Topic Sync management command."""

    def handle(self, *args: Any, **options: Any) -> None:
        logger.info("Fetching topics from API...")
        fetched_topics = _fetch_all_topics()
        logger.info("Fetched topics", extra={"count": len(fetched_topics)})

        logger.info("Syncing topics...")
        _sync_with_fetched_topics(fetched_topics)

        logger.info("Checking for removed topics...")
        _check_for_removed_topics({topic["id"] for topic in fetched_topics})

        logger.info("Finished syncing topics.")


def _fetch_all_topics() -> list[dict[str, str]]:
    """Collect a complete list of topics and their subtopics by doing a
    depth/breadth-first search using a stack of URLs.
    """
    topics = []

    if not settings.TOPIC_API_BASE_URL:
        raise ImproperlyConfigured('"TOPIC_API_BASE_URL" must be set')

    # Build a stack of topics URLs and parent IDs
    request_stack: list[tuple[str, str | None]] = [(settings.TOPIC_API_BASE_URL, None)]

    # Use the stack of subtopic URls to iterate through, fetching all the subtopics
    while request_stack:
        url, parent_id = request_stack.pop()
        raw_topics = _request_topics(url)

        # Extract just the fields we need
        subtopics = [
            {
                k: v
                for k, v in raw_topic.items()
                if k
                in {
                    "title",
                    "id",
                    "slug",
                    "description",
                }
            }
            for raw_topic in raw_topics
        ]

        for topic in subtopics:
            if parent_id:
                topic["parent_id"] = parent_id

        # Extend the topics list, to build a flat list of topics and subtopics which contain their own parent IDs
        topics.extend(subtopics)

        # Add any subtopics URLs from the topics we just fetched to the stack
        request_stack.extend(_extract_subtopic_links(raw_topics))

    return topics


def _request_topics(url: str) -> list[dict[str, Any]]:
    """Fetch topics from the API and return the items from the response."""
    topics_response = requests.get(url, timeout=30)
    topics_response.raise_for_status()
    raw_topics: list[dict[str, Any]] = topics_response.json().get("items", [])
    return raw_topics


def _extract_subtopic_links(raw_topics: Iterable[Mapping[str, Any]]) -> list[tuple[str, str | None]]:
    """Return a list of tuples of any subtopic links and their parent topic IDs found in raw_topics."""
    return [
        (subtopic_link, raw_topic["id"])
        for raw_topic in raw_topics
        # NOTE: This assumes we can simply call the links in the response as they are provided,
        # perhaps switch to building the URL ourselves
        if (
            (subtopic_link := raw_topic.get("links", {}).get("subtopics", {}).get("href"))
            and raw_topic.get("subtopics_ids")
        )
    ]


def _sync_with_fetched_topics(fetched_topics: Iterable[Mapping[str, str]]) -> None:
    """For each fetched topic, decide if it needs to be created, updated, or left as is."""
    _check_for_duplicate_topics(fetched_topics)

    updated_count = 0
    created_count = 0
    for fetched_topic in fetched_topics:
        if not fetched_topic.get("slug"):
            logger.warning("Cannot create or update topic: missing slug.", extra={"topic": fetched_topic["id"]})
            continue
        if existing_topic := _get_topic(fetched_topic["id"]):
            if not _topic_matches(existing_topic, fetched_topic):
                _update_topic(existing_topic, fetched_topic)
                updated_count += 1
        else:
            _create_topic(fetched_topic)
            created_count += 1

    logger.info("Saved new topic(s)", extra={"count": created_count})
    logger.info("Updated existing topic(s)", extra={"count": updated_count})


def _check_for_duplicate_topics(fetched_topics: Iterable[Mapping[str, str]]) -> None:
    topic_ids = set()
    for topic in fetched_topics:
        if topic["id"] in topic_ids:
            raise RuntimeError(f"Received duplicate topic ID in API responses, topic IDs must be unique: {topic['id']}")
        topic_ids.add(topic["id"])


def _get_topic(topic_id: str) -> Topic | None:
    """Fetches a Topic record by its primary key (id), or returns None if not found."""
    return Topic.objects.filter(id=topic_id).first()  # type: ignore[no-any-return]


def _topic_matches(existing_topic: Topic, fetched_topic: Mapping[str, str]) -> bool:
    """Compares: title, description, removed status, Parent ID.
    If all these match, the function returns True; otherwise False.
    """
    existing_parent = existing_topic.get_parent()
    existing_parent_id = existing_parent.id if existing_parent else None

    return (
        fetched_topic["title"] == existing_topic.title
        and fetched_topic.get("description") == existing_topic.description
        and fetched_topic.get("slug") == existing_topic.slug
        and not existing_topic.removed
        and existing_parent_id == fetched_topic.get("parent_id")
    )


def _update_topic(existing_topic: Topic, fetched_topic: Mapping[str, str]) -> None:
    """Updates an existing topic with data from an external source.

    - Updates `title`, `description`, and sets `removed = False` (as it is present in external data).
    - If the `parent_id` differs from the current parent, moves the topic to the new parent.
    - Logs changes and warnings when moving topics.
    """
    logger.info("Updating existing topic", extra={"topic": existing_topic.id, "fetched_topic": fetched_topic})
    existing_topic.title = fetched_topic.get("title")
    existing_topic.description = fetched_topic.get("description")
    existing_topic.slug = fetched_topic.get("slug")
    existing_topic.removed = False
    existing_topic.save()

    # If the topic parent has changed then move the node to match
    existing_parent_id: str | None = getattr(existing_topic.get_parent(), "id", None)
    new_parent_id: str | None = fetched_topic.get("parent_id")
    if existing_parent_id != new_parent_id:
        new_parent = _get_topic(new_parent_id) if new_parent_id else None
        if new_parent_id and not new_parent:
            raise RuntimeError(
                f"Parent topic destination with id {new_parent_id} doesn't exist for moving topic {existing_topic.id}"
            )
        logger.warning(
            "Moving topic to new parent",
            extra={
                "topic": existing_topic.id,
                "old_parent": existing_parent_id,
                "new_parent": new_parent.id if new_parent else None,
            },
        )
        existing_topic.move(new_parent)


def _create_topic(fetched_topic: Mapping[str, str]) -> None:
    """Creates a Topic object with the given id, title, slug, description, and parent."""
    logger.info("Saving new topic", extra={"topic": fetched_topic["id"]})
    new_topic = Topic(
        id=fetched_topic["id"],
        title=fetched_topic["title"],
        slug=fetched_topic.get("slug"),
        description=fetched_topic.get("description"),
    )
    if parent_id := fetched_topic.get("parent_id"):
        parent = _get_topic(parent_id)
        Topic.save_new(new_topic, parent_topic=parent)
    else:
        Topic.save_new(new_topic)


def _check_for_removed_topics(existing_topic_ids: set[str]) -> None:
    """Figures out which topics exist in the database but were not returned
    by the external API in this sync cycle.
    """
    existing_topics = _get_all_existing_topic_ids()
    removed_topics = existing_topics.difference(existing_topic_ids)
    if removed_topics:
        logger.warning("Found removed topic(s)", extra={"count": len(removed_topics)})
    for removed_topic_id in removed_topics:
        logger.warning("Marking topic as removed", extra={"topic": removed_topic_id})
        _set_topic_as_removed(removed_topic_id)


def _get_all_existing_topic_ids() -> set[str]:
    return set(Topic.objects.values_list("id", flat=True))


def _set_topic_as_removed(removed_topic_id: str) -> None:
    removed_topic = Topic.objects.get(id=removed_topic_id)
    removed_topic.removed = True
    removed_topic.save()
