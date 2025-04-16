from typing import TYPE_CHECKING

from rest_framework import serializers

from cms.search.utils import build_resource_dict

if TYPE_CHECKING:
    from wagtail.models import Page


class ResourceSerializer(serializers.Serializer):
    def create(self, validated_data: dict) -> None:
        """This serializer is read-only, so creation is not supported."""
        raise NotImplementedError("ResourceSerializer is read-only")

    def update(self, instance: object, validated_data: dict) -> None:
        """This serializer is read-only, so updates are not supported."""
        raise NotImplementedError("ResourceSerializer is read-only")

    def to_representation(self, instance: "Page") -> dict:
        return build_resource_dict(instance)
