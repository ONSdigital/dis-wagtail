from django.db import models
from wagtail.contrib.settings.models import register_setting

from cms.core.models.base import BaseSiteSetting
from cms.images.models import CustomImage

__all__ = [
    "SocialMediaSettings",
]


@register_setting
class SocialMediaSettings(BaseSiteSetting):
    """Settings class for social media settings."""

    default_sharing_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Default sharing text to use if social text has not been set on a page.",
    )
    default_sharing_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Default sharing image to use if social image has not been set on a page.",
    )
    site_name = models.CharField(
        max_length=255,
        blank=True,
        default="Office for National Statistics",
        help_text="Site name, used by Open Graph.",
    )
