import itertools
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.core.signals import setting_changed
from django.db.models.signals import pre_save
from django.utils.log import configure_logging
from wagtail.models import DraftStateMixin, Locale, Page, Revision, Site
from wagtail.signals import page_published, page_slug_changed, page_unpublished

from cms.core.templatetags.page_config_tags import get_page_config_cache_key

# Tree depth of the home page
HOME_PAGE_DEPTH = 2


def remove_go_live_seconds(
    sender: Any,  # pylint: disable=unused-argument
    instance: Page,
    raw: bool,  # pylint: disable=unused-argument
    using: str,  # pylint: disable=unused-argument
    update_fields: list[str] | None,
    **kwargs: Any,
) -> None:
    if (not update_fields or "go_live_at" in update_fields) and instance.go_live_at:
        instance.go_live_at = instance.go_live_at.replace(second=0)


def remove_approved_go_live_seconds(
    sender: Any,  # pylint: disable=unused-argument
    instance: Revision,
    raw: bool,  # pylint: disable=unused-argument
    using: str,  # pylint: disable=unused-argument
    update_fields: list[str] | None,
    **kwargs: Any,
) -> None:
    if (not update_fields or "approved_go_live_at" in update_fields) and instance.approved_go_live_at:
        instance.approved_go_live_at = instance.approved_go_live_at.replace(second=0)


def reload_logging_config(*, setting: str, **kwargs: Any) -> None:
    """Reload logging config when the relevant settings change.

    @see https://code.djangoproject.com/ticket/36958
    """
    if setting in {"LOGGING", "LOGGING_CONFIG"}:
        configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)


def invalidate_page_config_cache(sender: Any, instance: Page, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    cache.delete_many(
        [
            get_page_config_cache_key(site, instance, language_code)
            for site, language_code in itertools.product(Site.objects.all(), dict(settings.LANGUAGES).keys())
        ]
    )


def sync_alias_translation_slugs(sender: Any, instance: Page, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    # Don't attempt to sync slugs for children of the root page
    if instance.depth == HOME_PAGE_DEPTH:
        return

    # Only process the signal for instances with a locale matching the default language,
    # to avoid potential issues with circular updates between translations
    if not instance.locale_id or instance.locale_id != Locale.get_default().pk:
        return

    updatable_aliased_translations = (
        instance.get_translations().filter(alias_of__isnull=False).exclude(slug=instance.slug)
    )
    for translation in updatable_aliased_translations:
        translation.slug = instance.slug
        # Use save() to trigger any related functionality
        translation.save()


def sync_alias_last_published_at(sender: Any, instance: Page, alias: bool = False, **kwargs: Any) -> None:  # pylint: disable=unused-argument
    # Only handle alias publish events where last_published_at wasn't carried over from the revision
    if not alias or instance.last_published_at is not None:
        return

    # Wagtail populates the alias via the stored revision content, which predates the publish and
    # has last_published_at=None. Fetch the value directly from the source page and backfill it.
    source_last_published_at = (
        Page.objects.filter(pk=instance.alias_of_id).values_list("last_published_at", flat=True).first()
    )

    if source_last_published_at:
        Page.objects.filter(pk=instance.pk).update(last_published_at=source_last_published_at)
        instance.last_published_at = source_last_published_at


def register_signal_handlers() -> None:
    for model in apps.get_models():
        if issubclass(model, DraftStateMixin):
            pre_save.connect(remove_go_live_seconds, sender=model)

    pre_save.connect(remove_approved_go_live_seconds, sender=Revision)

    page_slug_changed.connect(sync_alias_translation_slugs)
    page_published.connect(sync_alias_last_published_at)

    setting_changed.connect(reload_logging_config)

    page_published.connect(invalidate_page_config_cache)
    page_unpublished.connect(invalidate_page_config_cache)
