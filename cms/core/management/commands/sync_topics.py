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
        logger.info(f"Fetched {len(topics)} topics")
        logger.info("Syncing topics...")
        sync_with_fetched_topics(topics)
        logger.info("Checking for removed topics...")
        check_removed_topics({topic["id"] for topic in topics})
        logger.info("Finished syncing topics.")


def fetch_all_topics() -> list[dict[str, str]]:
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
    topics_response = requests.get(url, timeout=30)
    topics_response.raise_for_status()

    return topics_response.json()["items"]


def extract_subtopic_links(raw_topics: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Return a list of tuples of any subtopic links and their parent topic IDs found in raw_topics."""
    return [
        (subtopic_link, raw_topic["id"])
        for raw_topic in raw_topics
        # NOTE: This assumes we can simply call the links in the response as they are provided
        if ((subtopic_link := raw_topic["links"].get("subtopics", {}).get("href")) and raw_topic["subtopics_ids"])
    ]


def sync_with_fetched_topics(fetched_topics: list[dict[str, str]]):
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

    logger.info(f"Saved {created_count} new topic(s)")
    logger.info(f"Updated {updated_count} existing topic(s)")


def get_topic(topic_id: str) -> Topic | None:
    return Topic.objects.filter(id=topic_id).first()


def topic_matches(existing_topic: Topic, fetched_topic: dict[str, str]) -> bool:
    existing_parent = existing_topic.get_parent()
    existing_parent_id = existing_parent.id if existing_parent else None

    return (
        fetched_topic["title"] == existing_topic.title
        and fetched_topic.get("description") == existing_topic.description
        and not existing_topic.removed
        and existing_parent_id == fetched_topic["parent_id"]
    )


def update_topic(existing_topic: Topic, fetched_topic: dict[str, str]):
    logger.info(f"Updating existing topic: {existing_topic.id} with fetched topic: {fetched_topic}")
    existing_topic.title = fetched_topic.get("title")
    existing_topic.description = fetched_topic.get("description")
    existing_topic.removed = False
    existing_topic.save()

    # If the topic parent has changed then move the node to match
    if (existing_parent := existing_topic.get_parent()) and existing_parent.id != fetched_topic["parent_id"]:
        logger.warning(
            f"Moving topic {existing_topic.id} "
            f"from parent {existing_parent.id} new parent {fetched_topic['parent_id']}. "
            f"This will also effect the path of {existing_topic.get_children_count()} subtopics."
        )
        existing_topic.move(get_topic(fetched_topic["parent_id"]), pos="sorted-child")


def create_topic(fetched_topic: dict[str, str]):
    logger.info(f"Saving new topic {fetched_topic}")
    new_topic = Topic(
        id=fetched_topic["id"], title=fetched_topic["title"], description=fetched_topic.get("description")
    )
    if fetched_topic["parent_id"]:
        parent = get_topic(fetched_topic["parent_id"])
        parent.add_child(instance=new_topic)
    else:
        Topic.add_root(instance=new_topic)


def check_removed_topics(existing_topic_ids: set[str]):
    existing_topics = get_all_existing_topic_ids()
    removed_topics = existing_topics.difference(existing_topic_ids)
    if removed_topics:
        logger.warning(f"WARNING: Found {len(removed_topics)} removed topic(s)")
    for removed_topic_id in removed_topics:
        logger.warning(f"Marking topic {removed_topic_id} as removed")
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
