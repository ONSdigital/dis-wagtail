import logging
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

from cache_memoize import cache_memoize
from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.utils.cache import patch_cache_control
from django.views.decorators.cache import cache_control
from django_redis.cache import RedisCache

logger = logging.getLogger(__name__)

memory_cache = partial(cache_memoize, cache_alias="memory")


class InvalidateReplayRedisCache(RedisCache):
    """A modified Redis cache backend which sends invalidations to another cache backend."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        try:
            self._replay_backend = caches["invalidate_replay"]
        except InvalidCacheBackendError as e:
            raise ImproperlyConfigured("Missing invalidate replay backend") from e

    def delete(self, key: Any, version: int | None = None) -> bool:  # pylint: disable=arguments-differ
        try:
            replay_result = self._replay_backend.delete(key, version)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Unable to replay delete", extra={"key": key, "version": version})
            replay_result = False

        return bool(super().delete(key, version) and replay_result)

    def delete_many(self, keys: Iterable[Any], version: int | None = None) -> None:  # pylint: disable=arguments-differ
        # Collect the keys immediately to ensure both backends receive the same keys.
        keys = list(keys)
        try:
            self._replay_backend.delete_many(keys, version)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Unable to replay delete_many", extra={"keys": keys, "version": version})

        super().delete_many(keys, version)


def get_default_cache_control_kwargs() -> dict[str, int | bool]:
    """Get browser Cache-Control parameters for semi-static HTML pages that are not
    covered by the 59 second publishing rule.
    """
    return {
        "public": True,
        "max_age": settings.CACHE_CONTROL_DEFAULT_MAX_AGE,
        "stale_while_revalidate": 0,
        "stale_if_error": settings.CACHE_CONTROL_DEFAULT_STALE_IF_ERROR,
    }


def get_publishing_rule_cache_control_kwargs() -> dict[str, int | bool]:
    """Get browser Cache-Control parameters for semi-static HTML pages covered by the 59
    second publishing rule.
    """
    return {
        "public": True,
        "max_age": settings.CACHE_CONTROL_PUBLISHING_RULE_MAX_AGE,
        "stale_while_revalidate": 0,
        "stale_if_error": settings.CACHE_CONTROL_PUBLISHING_RULE_STALE_IF_ERROR,
    }


def get_cdn_cache_control_header_value() -> str:
    """Get the value of the Cloudflare-CDN-Cache-Control header, used to set the edge cache
    TTL independently of the browser Cache-Control header. Same for all semi-static pages,
    as purges on publish keep the edge cache up to date.
    """
    return (
        f"max-age={settings.CACHE_CONTROL_CDN_MAX_AGE}, "
        f"stale-while-revalidate={settings.CACHE_CONTROL_CDN_STALE_WHILE_REVALIDATE}, "
        f"stale-if-error={settings.CACHE_CONTROL_CDN_STALE_IF_ERROR}"
    )


def get_default_cache_control_decorator() -> Callable:
    """Get cache control decorator that can be applied to views as a
    sane default for normal content pages.
    """
    return cache_control(**get_default_cache_control_kwargs())


def apply_page_cache_headers(page: Any, response: HttpResponse) -> HttpResponse:
    """Set the browser Cache-Control header and the edge Cloudflare-CDN-Cache-Control header
    on a page response, using the publishing rule TTLs for pages with
    `is_publishing_rule_page = True`, and the default semi-static TTLs otherwise.

    Uses the page that was actually rendered (from the response's context) rather than the
    routed page, since they can differ (e.g. an article series delegating to an edition).
    """
    rendered_page = getattr(response, "context_data", {}).get("self", page)
    cache_control_kwargs = (
        get_publishing_rule_cache_control_kwargs()
        if getattr(rendered_page, "is_publishing_rule_page", False)
        else get_default_cache_control_kwargs()
    )
    patch_cache_control(response, **cache_control_kwargs)
    response["Cloudflare-CDN-Cache-Control"] = get_cdn_cache_control_header_value()
    return response
