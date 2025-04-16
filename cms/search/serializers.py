from typing import TYPE_CHECKING

from rest_framework import serializers
from wagtail.rich_text import get_text_for_indexing

if TYPE_CHECKING:
    from wagtail.models import Page


class ResourceSerializer(serializers.Serializer):
    def create(self, validated_data: dict) -> None:
        """This serializer is read-only, so creation is not supported."""
        raise NotImplementedError("ResourceSerializer is read-only")

    def update(self, instance: object, validated_data: dict) -> None:
        """This serializer is read-only, so updates are not supported."""
        raise NotImplementedError("ResourceSerializer is read-only")

    uri = serializers.SerializerMethodField()
    content_type = serializers.CharField(source="search_index_content_type")
    summary = serializers.SerializerMethodField()
    title = serializers.CharField()
    topics = serializers.SerializerMethodField()
    release_date = serializers.SerializerMethodField(required=False)

    def get_uri(self, obj: "Page") -> str:
        return str(obj.url_path)

    def get_summary(self, obj: "Page") -> str:
        if hasattr(obj, "summary"):
            return str(get_text_for_indexing(obj.summary))
        return ""

    def get_topics(self, obj: "Page") -> list:
        return getattr(obj, "topic_ids", [])

    def get_release_date(self, obj: "Page") -> str | None:
        """Return the ISO-formatted 'release_date' if present on the page,
        else None.
        """
        if hasattr(obj, "release_date") and obj.release_date:
            return str(obj.release_date.isoformat())
        return None


class ReleaseResourceSerializer(ResourceSerializer):
    def create(self, validated_data: dict) -> None:
        """This serializer is read-only, so creation is not supported."""
        raise NotImplementedError("ResourceSerializer is read-only")

    def update(self, instance: object, validated_data: dict) -> None:
        """This serializer is read-only, so updates are not supported."""
        raise NotImplementedError("ResourceSerializer is read-only")

    release_date = serializers.SerializerMethodField()
    finalised = serializers.SerializerMethodField()
    cancelled = serializers.SerializerMethodField()
    published = serializers.SerializerMethodField()
    date_changes = serializers.SerializerMethodField()
    provisional_date = serializers.SerializerMethodField()

    def get_finalised(self, obj: "Page") -> bool:
        return obj.status in ["CONFIRMED", "PROVISIONAL"]

    def get_cancelled(self, obj: "Page") -> bool:
        return str(obj.status) == "CANCELLED"

    def get_published(self, obj: "Page") -> bool:
        return str(obj.status) == "PUBLISHED"

    def get_release_date(self, obj: "Page") -> str | None:
        if hasattr(obj, "release_date") and obj.release_date:
            return str(obj.release_date.isoformat())
        return None

    def get_date_changes(self, obj: "Page") -> list[dict[str, str]]:
        if hasattr(obj, "changes_to_release_date") and obj.changes_to_release_date:
            return [
                {
                    "change_notice": c.value.get("reason_for_change"),
                    "previous_date": c.value.get("previous_date").isoformat(),
                }
                for c in obj.changes_to_release_date
            ]
        return []

    def get_provisional_date(self, obj: "Page") -> str | None:
        """If the page has 'release_date_text', return it as 'provisional_date'."""
        return getattr(obj, "release_date_text", None) or None
