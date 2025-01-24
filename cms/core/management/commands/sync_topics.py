from typing import Any

import requests
from django.core.management import BaseCommand

from cms.taxonomy.models import Topic


class Command(BaseCommand):
    """Topic Sync management command."""

    def handle(self, *args: Any, **options: Any) -> None:
        print("Fetching topics from API...")
        topics = self.fetch_topics()
        print("Syncing topics...")
        self.sync_with_fetched_topics(topics)
        print("Checking for removed topics...")
        self.check_removed_topics({topic["id"] for topic in topics})
        print("Done.")

    def fetch_topics(self, topics_url="https://api.beta.ons.gov.uk/v1/topics") -> list[dict[str, str]]:
        topics = []

        # Build a stack of topics URLs and parent IDs
        request_stack = [(topics_url, None)]

        # Use the stack of subtopic URls to iterate through, fetching all the subtopics
        while request_stack:
            url, parent_id = request_stack.pop()
            raw_topics = self.request_topics(url)

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
            request_stack.extend(self.extract_subtopic_links(raw_topics))

        return topics

    def request_topics(self, url: str) -> list[dict[str, str]]:
        topics_response = requests.get(url, timeout=30)
        topics_response.raise_for_status()

        return topics_response.json()["items"]

    def extract_subtopic_links(self, raw_topics: list[dict[str, Any]]) -> list[tuple]:
        """Return a list of tuples of any subtopic links and their parent topic IDs found in raw_topics."""
        return [
            (subtopic_link, raw_topic["id"])
            for raw_topic in raw_topics
            if ((subtopic_link := raw_topic["links"].get("subtopics", {}).get("href")) and raw_topic["subtopics_ids"])
        ]

    def sync_with_fetched_topics(self, fetched_topics: list[dict[str, str]]):
        for fetched_topic in fetched_topics:
            if existing_topic := self.get_topic(fetched_topic["id"]):
                if not self.topic_matches(fetched_topic, existing_topic):
                    self.update_topic(existing_topic, fetched_topic)
            else:
                self.create_topic(fetched_topic)

    def get_topic(self, topic_id: str):
        return Topic.objects.get(id=topic_id)

    def topic_matches(self, topic, existing_topic: Topic):
        # TODO, compare fetched topic fields with existing topic object
        print("Checking if existing topic matches:", topic, existing_topic)
        return True

    def update_topic(self, existing_topic, fetched_topic: dict[str, str]):
        # TODO, overwrite the existing topic data
        print(f'Updating existing topic: {existing_topic['id']} with fetched topic: {fetched_topic}')

    def create_topic(self, fetched_topic):
        # TODO, save a new topic
        print(f"Saving new topic {fetched_topic}")

    def check_removed_topics(self, synced_topic_ids):
        # TODO, polish
        existing_topics = self.get_all_existing_topic_ids()
        removed_topics = existing_topics.difference(synced_topic_ids)
        if removed_topics:
            print(f"WARNING: Found {len(removed_topics)} removed topic(s)")
        for removed_topic_id in removed_topics:
            print(f"Marking topic {removed_topic_id} as removed")
            self.set_topic_as_removed(removed_topic_id)

    def get_all_existing_topic_ids(self):
        # TODO
        return set()

    def set_topic_as_removed(self, orphaned_topic_id):
        # TODO
        pass


def main():
    command = Command()
    command.handle()


if __name__ == "__main__":
    main()
