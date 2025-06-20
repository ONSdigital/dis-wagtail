from typing import TYPE_CHECKING, ClassVar, Optional, Self, cast

from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from wagtail.admin.panels import ObjectList, TabbedInterface
from wagtail.models import Page
from wagtail.query import PageQuerySet
from wagtail.utils.decorators import cached_classmethod

from cms.core.cache import get_default_cache_control_decorator
from cms.core.query import order_by_pk_position
from cms.taxonomy.forms import DeduplicateTopicsAdminForm

from ..forms import ONSCopyForm
from .mixins import ListingFieldsMixin, SocialFieldsMixin

if TYPE_CHECKING:
    from django.db import models
    from wagtail.admin.panels import FieldPanel
    from wagtail.contrib.settings.models import (
        BaseGenericSetting as _WagtailBaseGenericSetting,
    )
    from wagtail.contrib.settings.models import (
        BaseSiteSetting as _WagtailBaseSiteSetting,
    )
    from wagtail.models import Site

    class WagtailBaseSiteSetting(_WagtailBaseSiteSetting, models.Model):
        """Explicit class definition for type checking. Indicates we're inheriting from Django's model."""

    class WagtailBaseGenericSetting(_WagtailBaseGenericSetting, models.Model):
        """Explicit class definition for type checking. Indicates we're inheriting from Django's model."""
else:
    from wagtail.contrib.settings.models import (
        BaseGenericSetting as WagtailBaseGenericSetting,
    )
    from wagtail.contrib.settings.models import (
        BaseSiteSetting as WagtailBaseSiteSetting,
    )

__all__ = ["BasePage", "BaseSiteSetting"]


# Apply default cache headers on this page model's serve method.
@method_decorator(get_default_cache_control_decorator(), name="serve")
class BasePage(ListingFieldsMixin, SocialFieldsMixin, Page):  # type: ignore[django-manager-missing]
    """Base page class with listing and social fields additions as well as cache decorators."""

    base_form_class = DeduplicateTopicsAdminForm
    copy_form_class = ONSCopyForm

    show_in_menus_default = True
    # Used to check for the existence of equation and ONS embed blocks.
    # Update in your specific Page class if the StreamField using them is different.
    content_field_name: str = "content"

    # used a page type label in the front-end
    label = "Page"

    class Meta:
        abstract = True

    promote_panels: ClassVar[list["FieldPanel"]] = [
        *Page.promote_panels,
        *ListingFieldsMixin.promote_panels,
        *SocialFieldsMixin.promote_panels,
    ]

    additional_panel_tabs: ClassVar[list[tuple[list["FieldPanel"], str]]] = []

    @cached_classmethod
    def get_edit_handler(cls) -> TabbedInterface:  # pylint: disable=no-self-argument
        """Override the default edit handler property, enabling us to add editor tabs."""
        if hasattr(cls, "edit_handler"):
            edit_handler = cls.edit_handler
        else:
            # construct a TabbedInterface made up of content_panels, taxonomy panels,
            # promote_panels, settings_panels and any additional panel tabs, skipping
            # any which are empty
            tabs = []

            if cls.content_panels:
                tabs.append(ObjectList(cls.content_panels, heading="Content"))
            if taxonomy_panels := getattr(cls, "taxonomy_panels", None):
                tabs.append(ObjectList(taxonomy_panels, heading="Taxonomy"))
            if cls.additional_panel_tabs:
                for panels, heading in cls.additional_panel_tabs:
                    tabs.append(ObjectList(panels, heading=heading))
            if cls.promote_panels:
                tabs.append(ObjectList(cls.promote_panels, heading="Promote"))
            if cls.settings_panels:
                tabs.append(ObjectList(cls.settings_panels, heading="Settings"))

            edit_handler = TabbedInterface(tabs, base_form_class=cls.base_form_class)

        return edit_handler.bind_to_model(cls)

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
        """Checks if there are any equation blocks."""
        if (streamvalue := getattr(self, self.content_field_name)) and hasattr(
            streamvalue.stream_block, "has_equations"
        ):
            # run the check on the StreamBlock itself, if it supports it
            return bool(streamvalue.stream_block.has_equations(streamvalue))

        return False

    @cached_property
    def has_ons_embed(self) -> bool:
        """Checks if there are any ONS embed blocks."""
        if (streamvalue := getattr(self, self.content_field_name)) and hasattr(
            streamvalue.stream_block, "has_ons_embed"
        ):
            # run the check on the StreamBlock itself, if it supports it
            return bool(streamvalue.stream_block.has_ons_embed(streamvalue))

        return False


class BaseSiteSetting(WagtailBaseSiteSetting):
    """A customized site setting.

    - Use default values in external environment if an instance doesn't exist.
    - Use `.get` to ensure the read connection is used.
    """

    class Meta:
        abstract = True

    @classmethod
    def for_site(cls, site: Optional["Site"]) -> Self:
        """Get or create an instance of this setting for the site."""
        if site is None:
            raise cls.DoesNotExist(f"{cls} does not exist for site None.")

        queryset = cls.base_queryset()

        try:
            # Explicitly call `.get` first to ensure the
            # read connection is used.
            return cast(Self, queryset.get(site=site))
        except cls.DoesNotExist:
            if settings.IS_EXTERNAL_ENV:
                # In the external env, the database connection is read only,
                # so just use the default values if the instance doesn't exist.
                return cls(site=site)

            instance, _created = queryset.get_or_create(site=site)
            return cast(Self, instance)


class BaseGenericSetting(WagtailBaseGenericSetting):
    """A customized site setting.

    - Use default values in external environment if an instance doesn't exist.
    - Use `.first` to ensure the read connection is used.
    """

    class Meta:
        abstract = True

    @classmethod
    def _get_or_create(cls) -> Self:
        """Get or create an instance of this setting."""
        # First, try and find an instance using the read connection.
        instance = cls.base_queryset().first()

        if instance is not None:
            return cast(Self, instance)

        if settings.IS_EXTERNAL_ENV:
            # In the external env, the database connection is read-only,
            # so just use the default values if the instance doesn't exist.
            return cls()

        return cast(Self, cls.objects.create())
