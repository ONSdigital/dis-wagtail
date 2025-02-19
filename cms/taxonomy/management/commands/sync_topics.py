import logging
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
        topics = _fetch_all_topics()
        logger.info("Fetched %d topics", len(topics))

        logger.info("Syncing topics...")
        _sync_with_fetched_topics(topics)

        logger.info("Checking for removed topics...")
        _check_for_removed_topics({topic["id"] for topic in topics})

        logger.info("Finished syncing topics.")


def _fetch_all_topics() -> list[dict[str, str]]:
    """Collect a complete list of topics and their subtopics by doing a
    depth/breadth-first search using a stack of URLs.
    """
    topics = []

    if not settings.DP_TOPIC_API_URL:
        raise ImproperlyConfigured('"DP_TOPIC_API_URL" must be set')

    # Build a stack of topics URLs and parent IDs
    request_stack = [(f"{settings.DP_TOPIC_API_URL}/topics", None)]

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
                    "description",
                }
            }
            for raw_topic in raw_topics
        ]

        for topic in subtopics:
            topic["parent_id"] = parent_id

        # Extend the topics list, to build a flat list of topics and subtopics which contain their own parent IDs
        topics.extend(subtopics)

        # Add any subtopics URLs from the topics we just fetched to the stack
        request_stack.extend(_extract_subtopic_links(raw_topics))

    return topics


def _request_topics(url: str) -> list[dict[str, str]]:
    """Fetch topics from the API and return the items from the response."""
    topics_response = requests.get(url, timeout=30)
    topics_response.raise_for_status()

    return topics_response.json().get("items", [])


def _extract_subtopic_links(raw_topics: list[dict[str, Any]]) -> list[tuple[str, str]]:
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


def _sync_with_fetched_topics(fetched_topics: list[dict[str, str]]):
    """For each fetched topic, decide if it needs to be created, updated, or left as is."""
    _check_for_duplicate_topics(fetched_topics)

    updated_count = 0
    created_count = 0
    for fetched_topic in fetched_topics:
        if existing_topic := _get_topic(fetched_topic["id"]):
            if not _topic_matches(existing_topic, fetched_topic):
                _update_topic(existing_topic, fetched_topic)
                updated_count += 1
        else:
            _create_topic(fetched_topic)
            created_count += 1

    logger.info("Saved %d new topic(s)", created_count)
    logger.info("Updated %d existing topic(s)", updated_count)


def _check_for_duplicate_topics(fetched_topics: list[dict[str, str]]) -> None:
    topic_ids = set()
    for topic in fetched_topics:
        if topic["id"] in topic_ids:
            raise RuntimeError(f"Received duplicate topic ID in API responses, topic IDs must be unique: {topic['id']}")
        topic_ids.add(topic["id"])


def _get_topic(topic_id: str) -> Topic | None:
    """Fetches a Topic record by its primary key (id), or returns None if none is found."""
    return Topic.objects.filter(id=topic_id).first()


def _topic_matches(existing_topic: Topic, fetched_topic: dict[str, str]) -> bool:
    """Compares: title, description, removed status, Parent ID.
    If all these match, the function returns True; otherwise False.
    """
    existing_parent = existing_topic.get_parent()
    existing_parent_id = existing_parent.id if existing_parent else None

    return (
        fetched_topic["title"] == existing_topic.title
        and fetched_topic.get("description") == existing_topic.description
        and not existing_topic.removed
        and existing_parent_id == fetched_topic["parent_id"]
    )


def _update_topic(existing_topic: Topic, fetched_topic: dict[str, str]) -> None:
    """Sets: title, description, removed = False (since the topic is present in the external data,
    it cannot be considered removed). Parent/child changes: If the new parent_id is different from the old one,
    we do a tree move of the topic to the new parent.
    """
    logger.info("Updating existing topic: %s with fetched topic: %s", existing_topic.id, fetched_topic)
    existing_topic.title = fetched_topic.get("title")
    existing_topic.description = fetched_topic.get("description")
    existing_topic.removed = False
    existing_topic.save()

    # If the topic parent has changed then move the node to match
    existing_parent_id: str | None = getattr(existing_topic.get_parent(), "id", None)
    if existing_parent_id != fetched_topic["parent_id"]:
        logger.warning(
            "Moving topic %s from parent %s to new parent %s. This will also affect the path of %d subtopics.",
            existing_topic.id,
            existing_parent_id,
            fetched_topic["parent_id"],
            existing_topic.get_children_count(),
        )
        existing_topic.move(_get_topic(fetched_topic["parent_id"]), pos="sorted-child")


def _create_topic(fetched_topic: dict[str, str]) -> None:
    """Creates a Topic object with the given id, title, and description, and parent."""
    logger.info("Saving new topic %s", fetched_topic)
    new_topic = Topic(
        id=fetched_topic["id"], title=fetched_topic["title"], description=fetched_topic.get("description")
    )
    if fetched_topic["parent_id"]:
        parent = _get_topic(fetched_topic["parent_id"])
        new_topic.save_topic(parent_topic=parent)
    else:
        new_topic.save_topic()


def _check_for_removed_topics(existing_topic_ids: set[str]) -> None:
    """Figures out which topics exist in the database but were not returned
    by the external API in this sync cycle.
    """
    existing_topics = _get_all_existing_topic_ids()
    removed_topics = existing_topics.difference(existing_topic_ids)
    if removed_topics:
        logger.warning("WARNING: Found %d removed topic(s)", len(removed_topics))
    for removed_topic_id in removed_topics:
        logger.warning("Marking topic %s as removed", removed_topic_id)
        _set_topic_as_removed(removed_topic_id)


def _get_all_existing_topic_ids() -> set[str]:
    all_topics = Topic.objects.all()
    topic_ids = {topic.id for topic in all_topics}
    return topic_ids


def _set_topic_as_removed(removed_topic_id: str) -> None:
    removed_topic = _get_topic(removed_topic_id)
    removed_topic.removed = True
    removed_topic.save()
