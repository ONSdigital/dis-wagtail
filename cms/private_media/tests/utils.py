from collections.abc import Iterable

from wagtail.contrib.frontend_cache.backends import BaseBackend

PURGED_URLS = []


class MockFrontEndCacheBackend(BaseBackend):
    def purge(self, url: str) -> None:
        PURGED_URLS.append(url)

    def purge_batch(self, urls: Iterable[str]) -> None:
        PURGED_URLS.extend(urls)
