from typing import Any

from django.core.exceptions import ImproperlyConfigured
from wagtail.contrib.frontend_cache.backends import CloudflareBackend as WagtailCloudflareBackend


class CloudflareBackend(WagtailCloudflareBackend):
    """Wagtail's Cloudflare backend with a configurable purge batch size.

    Wagtail hardcodes CHUNK_SIZE, which is lower than what Cloudflare Enterprise allows.
    Remove this class once Wagtail supports configuring the batch size upstream.
    ref: https://github.com/wagtail/wagtail/issues/14352
    """

    def __init__(self, params: dict[str, Any]) -> None:
        batch_size = params.pop("PURGE_BATCH_SIZE", self.CHUNK_SIZE)
        super().__init__(params)
        try:
            batch_size = int(batch_size)
        except (TypeError, ValueError) as e:
            raise ImproperlyConfigured("'PURGE_BATCH_SIZE' must be a positive integer.") from e
        if batch_size < 1:
            raise ImproperlyConfigured("'PURGE_BATCH_SIZE' must be a positive integer.")
        self.CHUNK_SIZE = batch_size  # pylint: disable=invalid-name
