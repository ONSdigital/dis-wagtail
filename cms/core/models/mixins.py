from typing import TYPE_CHECKING, Any, ClassVar, Optional

from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db import models
from django.http import Http404
from wagtail.admin.panels import FieldPanel, MultiFieldPanel

if TYPE_CHECKING:
    from django.core.paginator import Page
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel

__all__ = ["ListingFieldsMixin", "SocialFieldsMixin", "LinkFieldsMixin", "SubpageMixin"]


class ListingFieldsMixin(models.Model):
    """Generic listing fields abstract class to add listing image/text to any new content type easily."""

    listing_image = models.ForeignKey(  # type: ForeignKey["CustomImage"]
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Choose the image you wish to be displayed when this page appears in listings",
    )
    listing_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Override the page title used when this page appears in listings",
    )
    listing_summary = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "The text summary used when this page appears in listings. It's also used as the "
            "description for search engines if the 'Meta description' field above is not defined."
        ),
    )

    class Meta:
        abstract = True

    promote_panels: ClassVar[list["Panel"]] = [
        MultiFieldPanel(
            heading="Listing information",
            children=[
                FieldPanel("listing_image"),
                FieldPanel("listing_title"),
                FieldPanel("listing_summary"),
            ],
        )
    ]


class SocialFieldsMixin(models.Model):
    """Generic social fields abstract class to add social image/text to any new content type easily."""

    social_image = models.ForeignKey(  # type: ForeignKey["CustomImage"]
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    social_text = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    promote_panels: ClassVar[list["Panel"]] = [
        MultiFieldPanel(
            heading="Social networks",
            children=[
                FieldPanel("social_image"),
                FieldPanel("social_text"),
            ],
        )
    ]


class LinkFieldsMixin(models.Model):
    """Adds fields for internal and external links with some methods to simplify the rendering.

    <a href="{{ obj.get_link_url }}">{{ obj.get_link_text }}</a>.
    """

    link_page = models.ForeignKey(  # type: ForeignKey[Page]
        "wagtailcore.Page", blank=True, null=True, on_delete=models.SET_NULL
    )
    link_url: str = models.URLField(blank=True)
    link_text: str = models.CharField(blank=True, max_length=255)

    class Meta:
        abstract = True

    def clean(self) -> None:
        """Validates that only link page or url are set, not both.

        And if choosing URL, the link text must be set.
        """
        if not self.link_page and not self.link_url:
            raise ValidationError(
                {
                    "link_url": ValidationError("You must specify link page or link url."),
                    "link_page": ValidationError("You must specify link page or link url."),
                }
            )

        if self.link_page and self.link_url:
            raise ValidationError(
                {
                    "link_url": ValidationError("You must specify link page or link url. You can't use both."),
                    "link_page": ValidationError("You must specify link page or link url. You can't use both."),
                }
            )

        if not self.link_page and not self.link_text:
            raise ValidationError(
                {"link_text": ValidationError("You must specify link text, if you use the link url field.")}
            )

    def get_link_text(self) -> str:
        """Returns the link text or linked_page link text."""
        if self.link_text:
            return self.link_text

        if self.link_page_id:
            return self.link_page.title

        return ""

    def get_link_url(self, request: Optional["HttpRequest"] = None) -> str:
        """Returns the link URL, with the chosen page taking precedence."""
        if self.link_page_id:
            return self.link_page.get_url(request=request)

        return self.link_url

    panels: ClassVar[list["Panel"]] = [
        MultiFieldPanel(
            [
                FieldPanel("link_page", heading="Page"),
                FieldPanel("link_url", heading="or URL"),
                FieldPanel("link_text", help_text="Required if adding a URL"),
            ],
            "Link",
        )
    ]


class SubpageMixin:
    """A helper that provides paginated subpages."""

    PAGE_SIZE = 24

    def get_paginator_page(self, request: "HttpRequest") -> "Page":
        """Returns the requested page from the list of public and published child pages."""
        children = self.get_children().live().public().specific()  # type: ignore[attr-defined]
        paginator = Paginator(children, per_page=self.PAGE_SIZE)
        try:
            return paginator.page(int(request.GET.get("p", 1)))
        except (EmptyPage, ValueError) as e:
            raise Http404 from e

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Add paginage subpages to the template context."""
        context: dict = super().get_context(request, *args, **kwargs)  # type: ignore[misc]
        context["subpages"] = self.get_paginator_page(request)
        return context
