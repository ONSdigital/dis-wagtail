from typing import TYPE_CHECKING, Any, ClassVar, Optional, Self, cast

from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import ObjectList, TabbedInterface
from wagtail.models import Page
from wagtail.query import PageQuerySet
from wagtail.utils.decorators import cached_classmethod
from wagtailschemaorg.models import PageLDMixin
from wagtailschemaorg.utils import extend

from cms.core.analytics_utils import format_date_for_gtm
from cms.core.cache import get_default_cache_control_decorator
from cms.core.forms import DeduplicateTopicsAdminForm, ONSCopyForm
from cms.core.permission_testers import BasePagePermissionTester
from cms.core.query import order_by_pk_position
from cms.taxonomy.mixins import ExclusiveTaxonomyMixin

from .mixins import ListingFieldsMixin, SocialFieldsMixin

if TYPE_CHECKING:
    from datetime import date, datetime

    from django.db import models
    from django.http import HttpRequest
    from wagtail.admin.panels import FieldPanel
    from wagtail.contrib.settings.models import (
        BaseGenericSetting as _WagtailBaseGenericSetting,
    )
    from wagtail.contrib.settings.models import (
        BaseSiteSetting as _WagtailBaseSiteSetting,
    )
    from wagtail.models import PagePermissionTester
    from wagtail.models.sites import Site, SiteRootPath

    class WagtailBaseSiteSetting(_WagtailBaseSiteSetting, models.Model):
        """Explicit class definition for type checking. Indicates we're inheriting from Django's model."""

    class WagtailBaseGenericSetting(_WagtailBaseGenericSetting, models.Model):
        """Explicit class definition for type checking. Indicates we're inheriting from Django's model."""

    from cms.users.models import User
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
class BasePage(PageLDMixin, ListingFieldsMixin, SocialFieldsMixin, Page):  # type: ignore[django-manager-missing]
    """Base page class with listing and social fields additions as well as cache decorators."""

    base_form_class = DeduplicateTopicsAdminForm
    copy_form_class = ONSCopyForm

    show_in_menus_default = True
    # Used to check for the existence of equation and ONS embed blocks.
    # Update in your specific Page class if the StreamField using them is different.
    content_field_name: str = "content"

    # used a page type label in the front-end
    label = "Page"

    # The default schema.org type for pages
    schema_org_type = "WebPage"

    class Meta:
        abstract = True

    promote_panels: ClassVar[list["FieldPanel"]] = [
        *Page.promote_panels,
        *ListingFieldsMixin.promote_panels,
        *SocialFieldsMixin.promote_panels,
    ]

    additional_panel_tabs: ClassVar[list[tuple[list["FieldPanel"], str]]] = []

    _analytics_content_type: ClassVar[str | None] = None

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

    def permissions_for_user(self, user: "User") -> "PagePermissionTester":
        """Override the permission tester class to use for our page models."""
        return BasePagePermissionTester(user, self)

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

    @property
    def publication_date(self) -> "date | datetime | None":
        """Return the publication date of the page."""
        # Use the release_date field if available, otherwise return last_published_at.
        return getattr(self, "release_date", self.last_published_at)

    def get_breadcrumbs(self, request: Optional["HttpRequest"] = None) -> list[dict[str, object]]:
        """Returns the breadcrumbs for the page as a list of dictionaries compatible with the ONS design system
        breadcrumbs component.
        """
        # TODO make request non-optional once wagtailschemaorg supports passing through the request.
        # https://github.com/neon-jungle/wagtail-schema.org/issues/29
        breadcrumbs = []
        homepage_depth = 2
        for ancestor_page in self.get_ancestors().specific().defer_streamfields():
            if ancestor_page.is_root():
                continue
            if ancestor_page.depth <= homepage_depth:
                breadcrumbs.append({"url": self.get_site().root_url, "text": _("Home")})
            elif not getattr(ancestor_page, "exclude_from_breadcrumbs", False):
                breadcrumbs.append({"url": ancestor_page.get_full_url(request=request), "text": ancestor_page.title})
        if request and getattr(request, "is_for_subpage", False):
            breadcrumbs.append({"url": self.get_full_url(request=request), "text": self.title})
        return breadcrumbs

    @cached_property
    def breadcrumbs_as_jsonld(self) -> dict[str, object]:
        """Returns the breadcrumbs as a dictionary in the format required for a JSON LD entity."""
        breadcrumbs_jsonld: dict[str, object] = {}
        item_list = []

        for position, breadcrumb in enumerate(self.get_breadcrumbs(), 1):
            item_list.append(
                {
                    "@type": "ListItem",
                    "position": position,
                    "name": str(breadcrumb["text"]),
                    "item": str(breadcrumb["url"]),
                }
            )

        if item_list:
            breadcrumbs_jsonld["breadcrumb"] = {
                "@type": "BreadcrumbList",
                "itemListElement": item_list,
            }

        return breadcrumbs_jsonld

    def ld_entity(self) -> dict[str, object]:
        """Add page breadcrumbs to the JSON LD properties."""
        page_ld_entity: dict[str, object] = {"@type": self.schema_org_type}
        page_ld_entity.update(self.breadcrumbs_as_jsonld)

        if not page_ld_entity.get("description", ""):
            page_ld_entity["description"] = self.search_description or self.listing_summary

        return cast(dict[str, Any], extend(super().ld_entity(), page_ld_entity))

    def get_canonical_url(self, request: "HttpRequest") -> str:
        """Get the default canonical URL for the page for the given request.
        This will normally be this page's full URL, except:
        - If this page is an alias, the canonical URL should be for the original, aliased page.
        - If the request is for a subpage (marked by setting the attribute `is_for_subpage=True` on the request object),
          then it will include the subpage route from the request.
        """
        canonical_page = self.alias_of or self
        if getattr(request, "is_for_subpage", False) and getattr(request, "routable_resolver_match", None):
            return request.build_absolute_uri(request.get_full_path())
        return cast(str, canonical_page.get_full_url(request=request))

    def get_url_parts(self, request: "Optional[HttpRequest]" = None) -> tuple[int, str, str] | None:
        """Override get_url_parts to generate URLs without trailing slashes."""
        parts = super().get_url_parts(request)

        if parts is None:
            return None

        site_id, root_url, page_path = parts

        if not settings.WAGTAIL_APPEND_SLASH and page_path and page_path != "/":
            page_path = page_path.rstrip("/")

        return site_id, root_url, page_path

    def get_relative_path(self, request: Optional["HttpRequest"] = None) -> str:
        """Get the relative path for this page, without the domain or any locale prefix.
        This will be the path portion of the URL returned by `get_url_parts()`.
        """
        parts = self.get_url_parts(request=request)  # returns site_id, root_url, page_path | None
        return parts[-1] if parts is not None else ""

    @cached_property
    def cached_analytics_values(self) -> dict[str, str | bool]:
        """Return a dictionary of the cachable analytics values for this page."""
        values = {"pageTitle": self.title}
        if content_type := self.analytics_content_type:
            values["contentType"] = content_type
        if content_group := self.analytics_content_group:
            values["contentGroup"] = content_group
        if content_theme := self.analytics_content_theme:
            values["contentTheme"] = content_theme
        if publication_date := self.publication_date:
            values["releaseDate"] = format_date_for_gtm(publication_date)
        return values

    def get_analytics_values(self, request: "HttpRequest") -> dict[str, str | bool]:
        """Return a dictionary of analytics values for this page.
        By default, this only returns the cached analytics values, but it exists to be overridden in places where the
        analytics values require the request object.
        """
        return self.cached_analytics_values

    @cached_property
    def parent_topic_or_theme(self) -> "BasePage | None":
        """Returns the first parent topic or theme page of this page (including this page itself, if it is a topic or
        theme page), if one exists.
        """
        for ancestor in self.get_ancestors(inclusive=True).reverse():
            if ancestor.specific_deferred.__class__.__name__ in ("TopicPage", "ThemePage"):
                return cast("BasePage", ancestor.specific_deferred)
        return None

    @property
    def analytics_content_type(self) -> str | None:
        """Returns the GTM content type for a page, if it has one."""
        return self._analytics_content_type

    @cached_property
    def analytics_content_group(self) -> str | None:
        """Returns the GTM content group for a page, if it has one.
        This is the slug of the topic associated with the page, for a theme or topic page this will be it's own slug,
        otherwise it will be the slug of the parent topic page if it exists.
        """
        if parent_topic_or_theme := self.parent_topic_or_theme:
            return cast(str, parent_topic_or_theme.slug)
        return None

    @cached_property
    def analytics_content_theme(self) -> str | None:
        """Returns the title of the top ancestor taxonomic topic for the pages parent topic or theme page,
        if one exists.
        """
        if not self.parent_topic_or_theme:
            return None
        parent_topic_or_theme = cast(ExclusiveTaxonomyMixin, self.parent_topic_or_theme)
        page_topic = parent_topic_or_theme.topic
        if not page_topic:
            return None

        parent_theme = page_topic.get_base_parent()
        return cast(str, parent_theme.title)

    def _get_site_root_paths(self, request: Optional["HttpRequest"] = None) -> list["SiteRootPath"]:
        """Extends the core Page._get_site_root_paths to account for alternative domains."""
        if not settings.CMS_USE_SUBDOMAIN_LOCALES:
            return cast(list["SiteRootPath"], super()._get_site_root_paths(request=request))

        from cms.locale.utils import get_mapped_site_root_paths  # pylint: disable=import-outside-toplevel

        cache_object = request if request else self
        try:
            # pylint: disable=protected-access
            cached_paths: list[SiteRootPath] = cache_object._wagtail_cached_site_root_paths  # type: ignore[union-attr]
            # pylint: enable=protected-access
            return cached_paths
        except AttributeError:
            paths = get_mapped_site_root_paths(request.get_host() if request is not None else None)
            # pylint: disable=protected-access,attribute-defined-outside-init
            cache_object._wagtail_cached_site_root_paths = paths  # type: ignore[union-attr]
            # pylint: enable=protected-access,attribute-defined-outside-init
            return paths


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
