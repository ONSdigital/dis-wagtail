from typing import ClassVar

from django.core.paginator import EmptyPage, Paginator
from django.db import models
from django.http import Http404
from wagtail.admin.panels import FieldPanel, MultiFieldPanel

__all__ = [
    "ListingFieldsMixin",
    "SocialFieldsMixin",
]


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
            "The text summary used when this page appears in listings. It's also used as the "
            "description for search engines if the 'Meta description' field above is not defined."
        ),
    )

    class Meta:
        abstract = True

    promote_panels: ClassVar[list[FieldPanel]] = [
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

    promote_panels: ClassVar[list[FieldPanel]] = [
        MultiFieldPanel(
            heading="Social networks",
            children=[
                FieldPanel("social_image"),
                FieldPanel("social_text"),
            ],
        )
    ]


class SubpageMixin:
    PAGE_SIZE = 24

    def get_paginator_page(self, request):
        paginator = Paginator(self.get_children().live().public().specific(), per_page=self.PAGE_SIZE)
        try:
            return paginator.page(int(request.GET.get("p", 1)))
        except (EmptyPage, ValueError) as e:
            raise Http404 from e

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["subpages"] = self.get_paginator_page(request)
        return context
