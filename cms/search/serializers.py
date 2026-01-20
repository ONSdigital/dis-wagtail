from typing import TYPE_CHECKING

from rest_framework import serializers

from cms.search.utils import build_resource_dict

if TYPE_CHECKING:
    from wagtail.models import Page


class ResourceSerializer(serializers.BaseSerializer):  # pylint: disable=abstract-method
    def to_representation(self, instance: Page) -> dict:
        return build_resource_dict(instance)
