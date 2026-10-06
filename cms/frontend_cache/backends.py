from typing import Any

from wagtail.contrib.frontend_cache.backends import CloudflareBackend as WagtailCloudflareBackend


class CloudflareBackend(WagtailCloudflareBackend):
    """Wagtail's Cloudflare backend with a configurable purge batch size.

    Wagtail hardcodes CHUNK_SIZE, which is lower than what Cloudflare Enterprise allows.
    Remove this class once Wagtail supports configuring the batch size upstream.
    ref: https://github.com/wagtail/wagtail/issues/14352
    """

    CHUNK_SIZE: int

    def __init__(self, params: dict[str, Any]) -> None:
        batch_size = params.pop("PURGE_BATCH_SIZE", self.CHUNK_SIZE)
        super().__init__(params)
        self.CHUNK_SIZE = batch_size  # pylint: disable=invalid-name
