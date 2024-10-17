from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from wagtail.models import Page
from wagtail.query import PageQuerySet

from cms.core.cache import get_default_cache_control_decorator
from cms.core.query import order_by_pk_position

from .mixins import ListingFieldsMixin, SocialFieldsMixin

__all__ = [
    "BasePage",
]


# Apply default cache headers on this page model's serve method.
@method_decorator(get_default_cache_control_decorator(), name="serve")
class BasePage(ListingFieldsMixin, SocialFieldsMixin, Page):
    show_in_menus_default = True

    class Meta:
        abstract = True

    promote_panels = Page.promote_panels + ListingFieldsMixin.promote_panels + SocialFieldsMixin.promote_panels

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
