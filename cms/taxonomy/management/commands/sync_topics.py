import logging
from typing import Any

import requests
from django.conf import settings
from django.core.management import BaseCommand

from cms.taxonomy.models import Topic

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Topic Sync management command."""

    def handle(self, *args: Any, **options: Any) -> None:
        logger.info("Fetching topics from API...")
        topics = fetch_all_topics()
        logger.info("Fetched %d topics", len(topics))

        logger.info("Syncing topics...")
        sync_with_fetched_topics(topics)

        logger.info("Checking for removed topics...")
        check_removed_topics({topic["id"] for topic in topics})

        logger.info("Finished syncing topics.")


def fetch_all_topics() -> list[dict[str, str]]:
    """Collect a complete list of topics and their subtopics by doing a
    depth/breadth-first search using a stack of URLs.
    """
    topics = []

    # Build a stack of topics URLs and parent IDs
    request_stack = [(f"{settings.DP_TOPIC_API_URL}/topics", None)]

    # Use the stack of subtopic URls to iterate through, fetching all the subtopics
    while request_stack:
        url, parent_id = request_stack.pop()
        raw_topics = request_topics(url)

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
        request_stack.extend(extract_subtopic_links(raw_topics))

    return topics


def request_topics(url: str) -> list[dict[str, str]]:
    """Fetch topics from the API and return the items from the response."""
    topics_response = requests.get(url, timeout=30)
    topics_response.raise_for_status()

    return topics_response.json().get("items", [])


def extract_subtopic_links(raw_topics: list[dict[str, Any]]) -> list[tuple[str, str]]:
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


def sync_with_fetched_topics(fetched_topics: list[dict[str, str]]):
    """For each fetched topic, decide if it needs to be created, updated, or left as is."""
    check_for_duplicate_topics(fetched_topics)

    updated_count = 0
    created_count = 0
    for fetched_topic in fetched_topics:
        if existing_topic := get_topic(fetched_topic["id"]):
            if not topic_matches(existing_topic, fetched_topic):
                update_topic(existing_topic, fetched_topic)
                updated_count += 1
        else:
            create_topic(fetched_topic)
            created_count += 1

    logger.info("Saved %d new topic(s)", created_count)
    logger.info("Updated %d existing topic(s)", updated_count)


def check_for_duplicate_topics(fetched_topics: list[dict[str, str]]) -> None:
    topic_ids = set()
    for topic in fetched_topics:
        if topic["id"] in topic_ids:
            raise RuntimeError(f"Received duplicate topic ID in API responses, topic IDs must be unique: {topic['id']}")
        topic_ids.add(topic["id"])


def get_topic(topic_id: str) -> Topic | None:
    """Fetches a Topic record by its primary key (id), or returns None if none is found."""
    return Topic.objects.filter(id=topic_id).first()


def topic_matches(existing_topic: Topic, fetched_topic: dict[str, str]) -> bool:
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


def update_topic(existing_topic: Topic, fetched_topic: dict[str, str]):
    """Sets: title, description, removed = False (since the topic is present in the external data,
    it cannot be considered removed). Parent/child changes: If the new parent_id is different from the old one,
    we do a tree move of the topic to the new parent.
    """
    logger.info("Updating existing topic: %s with fetched topic: %s", existing_topic.id, fetched_topic)
    existing_topic.title = fetched_topic.get("title")
    existing_topic.description = fetched_topic.get("description")
    existing_topic.removed = False
    existing_topic.save()

    # Raise an error if there is an invalid topic move
    if fetched_topic.get("parent_id") and existing_topic.is_root():
        raise RuntimeError("Received an invalid response attempting to move a root topic to a non-root position.")
    if not existing_topic.is_root() and not fetched_topic.get("parent_id"):
        raise RuntimeError("Received an invalid response attempting to move a non-root topic to a root position.")

    # If the topic parent has changed then move the node to match
    if (existing_parent := existing_topic.get_parent()) and existing_parent.id != fetched_topic["parent_id"]:
        logger.warning(
            "Moving topic %s from parent %s to new parent %s. This will also affect the path of %d subtopics.",
            existing_topic.id,
            existing_parent.id,
            fetched_topic["parent_id"],
            existing_topic.get_children_count(),
        )
        existing_topic.move(get_topic(fetched_topic["parent_id"]), pos="sorted-child")


def create_topic(fetched_topic: dict[str, str]):
    """Creates a Topic object with the given id, title, and description,
    If a parent ID is specified, we call parent.add_child,
    Otherwise, we call Topic.add_root.
    """
    # TODO create a dummy root level topic so all actual topics are not root and can be moved freely
    logger.info("Saving new topic %s", fetched_topic)
    new_topic = Topic(
        id=fetched_topic["id"], title=fetched_topic["title"], description=fetched_topic.get("description")
    )
    if fetched_topic["parent_id"]:
        parent = get_topic(fetched_topic["parent_id"])
        parent.add_child(instance=new_topic)
    else:
        Topic.add_root(instance=new_topic)


def check_removed_topics(existing_topic_ids: set[str]):
    """Figures out which topics exist in the database but were not returned
    by the external API in this sync cycle.
    """
    existing_topics = get_all_existing_topic_ids()
    removed_topics = existing_topics.difference(existing_topic_ids)
    if removed_topics:
        logger.warning("WARNING: Found %d removed topic(s)", len(removed_topics))
    for removed_topic_id in removed_topics:
        logger.warning("Marking topic %s as removed", removed_topic_id)
        set_topic_as_removed(removed_topic_id)


def get_all_existing_topic_ids() -> set[str]:
    all_topics = Topic.objects.all()
    topic_ids = {topic.id for topic in all_topics}
    return topic_ids


def set_topic_as_removed(removed_topic_id: str):
    removed_topic = get_topic(removed_topic_id)
    removed_topic.removed = True
    removed_topic.save()


def main():
    command = Command()
    command.handle()


if __name__ == "__main__":
    main()
