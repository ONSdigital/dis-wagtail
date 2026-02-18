import logging

from wagtail.contrib.frontend_cache.backends import BaseBackend

logger = logging.getLogger(__name__)


class DummyFrontEndCacheBackend(BaseBackend):
    def purge(self, url: str) -> None:
        logger.info("Purging %s", url)
