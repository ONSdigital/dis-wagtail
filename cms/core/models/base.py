from functools import cached_property
from typing import TYPE_CHECKING, ClassVar

from django.utils.decorators import method_decorator
from wagtail.models import Page
from wagtail.query import PageQuerySet

from cms.core.cache import get_default_cache_control_decorator
from cms.core.query import order_by_pk_position

from .mixins import ListingFieldsMixin, SocialFieldsMixin

if TYPE_CHECKING:
    from wagtail.admin.panels import FieldPanel


__all__ = [
    "BasePage",
]


# Apply default cache headers on this page model's serve method.
@method_decorator(get_default_cache_control_decorator(), name="serve")
class BasePage(ListingFieldsMixin, SocialFieldsMixin, Page):  # type: ignore[django-manager-missing]
    """Base page class with listing and social fields additions as well as cache decorators."""

    show_in_menus_default = True
    # Used to check for the existence of equation and ONS embed blocks.
    # Update in your specific Page class if the StreamField using them is different.
    content_field_name: str = "content"

    class Meta:
        abstract = True

    promote_panels: ClassVar[list["FieldPanel"]] = [
        *Page.promote_panels,
        *ListingFieldsMixin.promote_panels,
        *SocialFieldsMixin.promote_panels,
    ]

    @cached_property
    def related_pages(self) -> PageQuerySet:
        """Return a `PageQuerySet` of items related to this page via the
        `PageRelatedPage` through model, and are suitable for display.
        The result is ordered to match that specified by editors using
        the 'page_related_pages' `InlinePanel`.
        """
        # NOTE: avoiding values_list() here for compatibility with preview
        # See: https://github.com/wagtail/django-modelcluster/issues/30
        ordered_page_pks = tuple(item.page_id for item in self.page_related_pages.all())
        return order_by_pk_position(
            Page.objects.live().public().specific(),
            pks=ordered_page_pks,
            exclude_non_matches=True,
        )

    @cached_property
    def has_equations(self) -> bool:
        """Checks if there are any equation blocks.
        Override in your specific Page class if the StreamField structure is different.
        """
        if streamfield := getattr(self, self.content_field_name):
            try:
                return streamfield.first_block_by_name(block_name="equation") is not None
            except AttributeError:
                return False

        return False

    @cached_property
    def has_ons_embed(self) -> bool:
        """Checks if there are any ONS embed blocks.
        Override in your specific Page class if the StreamField structure is different.
        """
        if streamfield := getattr(self, self.content_field_name):
            try:
                return streamfield.first_block_by_name(block_name="ons_embed") is not None
            except AttributeError:
                return False

        return False
