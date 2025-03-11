from typing import ClassVar

from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import register_setting
from wagtail.fields import RichTextField

from cms.core.models.base import BaseSiteSetting
from cms.images.models import CustomImage

__all__ = [
    "SocialMediaSettings",
    "SystemMessagesSettings",
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


@register_setting
class SystemMessagesSettings(BaseSiteSetting):
    """Settings class for global system messages."""

    class Meta:
        verbose_name = "system messages"

    title_404 = models.CharField("Title", max_length=255, default="Page not found")
    body_404 = RichTextField(
        "Text",
        default="<p>You may be trying to find a page that doesn&rsquo;t exist or has been moved.</p>",
    )

    panels: ClassVar[list[FieldPanel]] = [MultiFieldPanel(["title_404", "body_404"], "404 page")]
