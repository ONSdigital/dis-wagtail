from typing import TYPE_CHECKING, Any, ClassVar

from django.core.paginator import EmptyPage, Paginator
from django.db import models
from django.http import Http404
from wagtail.admin.panels import MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin
from wagtail.coreutils import WAGTAIL_APPEND_SLASH

if TYPE_CHECKING:
    from django.core.paginator import Page
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel

__all__ = ["ListingFieldsMixin", "SocialFieldsMixin", "SubpageMixin"]


class ListingFieldsMixin(models.Model):
    """Generic listing fields abstract class to add listing image/text to any new content type easily."""

    listing_image = models.ForeignKey(
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
            "The text summary used when this page appears in listings. It’s also used as the "
            "description for search engines if the 'Meta description' field above is not defined."
        ),
    )

    class Meta:
        abstract = True

    promote_panels: ClassVar[list[Panel]] = [
        MultiFieldPanel(
            heading="Listing information",
            children=[
                "listing_image",
                "listing_title",
                "listing_summary",
            ],
        )
    ]


class SocialFieldsMixin(models.Model):
    """Generic social fields abstract class to add social image/text to any new content type easily."""

    social_image = models.ForeignKey(
        "images.CustomImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    social_text = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    promote_panels: ClassVar[list[Panel]] = [
        MultiFieldPanel(
            heading="Social networks",
            children=[
                "social_image",
                "social_text",
            ],
        )
    ]


class SubpageMixin:
    """A helper that provides paginated subpages."""

    PAGE_SIZE = 24

    def get_paginator_page(self, request: HttpRequest) -> Page:
        """Returns the requested page from the list of public and published child pages."""
        children = self.get_children().live().public().specific()  # type: ignore[attr-defined]
        paginator = Paginator(children, per_page=self.PAGE_SIZE)
        try:
            return paginator.page(int(request.GET.get("p", 1)))
        except (EmptyPage, ValueError) as e:
            raise Http404 from e

    def get_context(self, request: HttpRequest, *args: Any, **kwargs: Any) -> dict:
        """Add paginated subpages to the template context."""
        context: dict = super().get_context(request, *args, **kwargs)  # type: ignore[misc]
        context["subpages"] = self.get_paginator_page(request)
        return context


class NoTrailingSlashRoutablePageMixin(RoutablePageMixin):
    """A mixin to remove trailing slashes from RoutablePage routes.
    This ensures that the output of routablepageurl and reverse_subpage does not
    include a trailing slash.
    """

    def reverse_subpage(self, name: str, args: list[str] | None = None, kwargs: dict[str, Any] | None = None) -> str:
        result: str = super().reverse_subpage(name, args, kwargs)
        if not WAGTAIL_APPEND_SLASH:
            result = result.rstrip("/")
        return result
