from rest_framework import serializers
from wagtail.rich_text import get_text_for_indexing


class ResourceSerializer(serializers.Serializer):
    uri = serializers.SerializerMethodField()
    content_type = serializers.CharField(source="search_index_content_type")
    summary = serializers.SerializerMethodField()
    title = serializers.CharField()
    topics = serializers.SerializerMethodField()
    release_date = serializers.SerializerMethodField(required=False)

    def get_uri(self, obj):
        return obj.url_path

    def get_summary(self, obj):
        if hasattr(obj, "summary"):
            return get_text_for_indexing(obj.summary)
        return ""

    def get_topics(self, obj):
        if hasattr(obj, "topic_ids"):
            return obj.topic_ids
        return []

    def get_release_date(self, obj):
        """Return the ISO-formatted 'release_date' if present on the page,
        else None.
        """
        if hasattr(obj, "release_date") and obj.release_date:
            return obj.release_date.isoformat()
        return None


class ReleaseResourceSerializer(ResourceSerializer):
    release_date = serializers.SerializerMethodField()
    finalised = serializers.SerializerMethodField()
    cancelled = serializers.SerializerMethodField()
    published = serializers.SerializerMethodField()
    date_changes = serializers.SerializerMethodField()
    provisional_date = serializers.SerializerMethodField()

    def get_finalised(self, obj):
        return obj.status in ["CONFIRMED", "PROVISIONAL"]

    def get_cancelled(self, obj):
        return obj.status == "CANCELLED"

    def get_published(self, obj):
        return obj.status == "PUBLISHED"

    def get_release_date(self, obj):
        if hasattr(obj, "release_date") and obj.release_date:
            return obj.release_date.isoformat()
        return None

    def get_date_changes(self, obj):
        if hasattr(obj, "changes_to_release_date") and obj.changes_to_release_date:
            return [
                {
                    "change_notice": c.value.get("reason_for_change"),
                    "previous_date": c.value.get("previous_date").isoformat(),
                }
                for c in obj.changes_to_release_date
            ]
        return []

    def get_provisional_date(self, obj):
        """If the page has 'release_date_text', return it as 'provisional_date'."""
        if hasattr(obj, "release_date_text") and obj.release_date_text:
            return obj.release_date_text
        return None
