import logging
from collections.abc import Callable, Iterable
from functools import partial
from typing import Any

from cache_memoize import cache_memoize
from django.conf import settings
from django.core.cache import InvalidCacheBackendError, caches
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.cache import cache_control
from django_redis.cache import RedisCache
from wagtail.contrib.frontend_cache.utils import purge_url_from_cache
from wagtail.models import Site

logger = logging.getLogger(__name__)


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


def purge_cache_on_all_sites(path: str) -> None:
    """Purge the given path on all defined sites."""
    if settings.DEBUG:
        return

    for site in Site.objects.all():
        purge_url_from_cache(site.root_url.rstrip("/") + path)


def get_default_cache_control_kwargs() -> dict[str, int | bool]:
    """Get cache control parameters used by the cache control decorators
    used by default on most pages. These parameters are meant to be
    sane defaults that can be applied to a standard content page.
    """
    s_maxage = getattr(settings, "CACHE_CONTROL_S_MAXAGE", None)
    stale_while_revalidate = getattr(settings, "CACHE_CONTROL_STALE_WHILE_REVALIDATE", None)
    cache_control_kwargs = {
        "s_maxage": s_maxage,
        "stale_while_revalidate": stale_while_revalidate,
        "public": True,
    }
    return {k: v for k, v in cache_control_kwargs.items() if v is not None}


def get_default_cache_control_decorator() -> Callable:
    """Get cache control decorator that can be applied to views as a
    sane default for normal content pages.
    """
    cache_control_kwargs = get_default_cache_control_kwargs()
    return cache_control(**cache_control_kwargs)


memory_cache = partial(cache_memoize, cache_alias="memory")
