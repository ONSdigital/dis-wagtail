from typing import TYPE_CHECKING, Any, ClassVar

from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db import models
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel

from cms.taxonomy.models import Topic
from cms.taxonomy.viewsets import ExclusiveTopicChooserWidget

if TYPE_CHECKING:
    from django.core.paginator import Page
    from django.http import HttpRequest
    from wagtail.admin.panels import Panel

__all__ = ["ExclusiveTaxonomyMixin", "GenericTaxonomyMixin", "ListingFieldsMixin", "SocialFieldsMixin", "SubpageMixin"]


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

    promote_panels: ClassVar[list["Panel"]] = [
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

    promote_panels: ClassVar[list["Panel"]] = [
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

    def get_paginator_page(self, request: "HttpRequest") -> "Page":
        """Returns the requested page from the list of public and published child pages."""
        children = self.get_children().live().public().specific()  # type: ignore[attr-defined]
        paginator = Paginator(children, per_page=self.PAGE_SIZE)
        try:
            return paginator.page(int(request.GET.get("p", 1)))
        except (EmptyPage, ValueError) as e:
            raise Http404 from e

    def get_context(self, request: "HttpRequest", *args: Any, **kwargs: Any) -> dict:
        """Add paginated subpages to the template context."""
        context: dict = super().get_context(request, *args, **kwargs)  # type: ignore[misc]
        context["subpages"] = self.get_paginator_page(request)
        return context


class GenericTaxonomyMixin(models.Model):
    """Generic Taxonomy mixin allows pages to be tagged with one or more topics non-exclusively."""

    taxonomy_panels: ClassVar[list["Panel"]] = [
        InlinePanel("topics", label=_("Topics")),
    ]

    class Meta:
        abstract = True


class ExclusiveTaxonomyMixin(models.Model):
    """A mixin that allows pages to be linked exclusively to a topic."""

    # Note that this is intended to behave as a one-to-one relationship, but multilingual versions of the same page
    # will need to be linked to the same topic, so we need to use a ForeignKey and enforce exclusivity separately
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, related_name="related_%(class)s", null=True)

    taxonomy_panels: ClassVar[list["Panel"]] = [
        FieldPanel("topic", widget=ExclusiveTopicChooserWidget),
    ]

    class Meta:
        abstract = True

    def clean(self):
        super().clean()

        if not self.topic:
            raise ValidationError({"topic": _("A topic is required.")})

        for sub_page_type in ExclusiveTaxonomyMixin.__subclasses__():
            # Check if other pages are exclusively linked to this topic.
            # Translations of the same page are allowed, but other pages aren't.
            # TODO for multilingual support, this will need to exclude different language versions of the same page by
            # excluding matching translation_keys
            if sub_page_type.objects.filter(topic=self.topic).exclude(pk=self.pk).exists():
                raise ValidationError({"topic": _("This topic is already linked to another theme or topic page.")})
