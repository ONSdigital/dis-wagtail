import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings

from cms.core.blocks.constants import CHART_BLOCK_TYPES
from cms.datavis.clients.chart_exporter import (
    ChartExporterClient,
    ChartExporterError,
    ChartExporterMalformedRequest,
    ChartExporterUnavailable,
    ChartObjectResponse,
)
from cms.datavis.models import RenderedChartImage
from cms.datavis.utils import hash_chart_config

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from wagtail.blocks.stream_block import StreamChild, StreamValue

logger = logging.getLogger(__name__)

GENERIC_RENDER_ERROR = "This chart could not be rendered. Please contact support."
UNAVAILABLE_RENDER_ERROR = "The chart rendering service is temporarily unavailable. Please try again."


@dataclass(frozen=True)
class ChartRenderResult:
    block_id: str
    changed: bool
    error: str | None = None


@dataclass(frozen=True)
class ChartFetched:
    """A chart image is ready to be created from this exporter response."""

    response: ChartObjectResponse
    config_hash: str


def iter_chart_blocks(value: StreamValue | None) -> Iterator[StreamChild]:
    """Recursively yield chart blocks from a StreamValue, including those nested in sections."""
    if not value:
        return
    for block in value:
        if block.block_type == "section":
            yield from iter_chart_blocks(block.value.get("content"))
        elif block.block_type in CHART_BLOCK_TYPES:
            yield block


def _fetch_chart_response(block: StreamChild, client: ChartExporterClient) -> ChartFetched | ChartRenderResult:
    """Do the (slow, network-bound) part of rendering a chart block.

    Safe to run off the main thread: it only calls out to the exporter and never touches the
    database. Returns a final ``ChartRenderResult`` when there's nothing left to do, or a
    ``ChartFetched`` when a chart image still needs to be created from the response.
    """
    config = block.block.get_export_config(block.value)
    config_hash = hash_chart_config(config)

    existing = block.value.get("rendered_chart_image")
    if isinstance(existing, RenderedChartImage) and existing.config_hash == config_hash:
        return ChartRenderResult(block_id=block.id, changed=False)

    try:
        response = client.create_chart(config)
    except ChartExporterMalformedRequest:
        return ChartRenderResult(block_id=block.id, changed=False, error=GENERIC_RENDER_ERROR)
    except ChartExporterUnavailable:
        return ChartRenderResult(block_id=block.id, changed=False, error=UNAVAILABLE_RENDER_ERROR)
    except ChartExporterError:
        return ChartRenderResult(block_id=block.id, changed=False, error=GENERIC_RENDER_ERROR)

    if response is None:
        # Integration disabled: nothing to attach.
        return ChartRenderResult(block_id=block.id, changed=False)

    return ChartFetched(response=response, config_hash=config_hash)


def render_chart_blocks(blocks: Iterable[StreamChild]) -> list[ChartRenderResult]:
    """Render (or reuse) chart images for the given chart blocks, in place.

    Each block's ``rendered_chart_image`` value is updated directly when a new image is
    created or reused. Blocks whose config hash already matches their currently attached
    image are skipped, so unchanged charts are not re-rendered on resubmission.
    """
    blocks = list(blocks)
    if not blocks:
        return []

    client = ChartExporterClient()
    start = time.monotonic()

    with ThreadPoolExecutor(max_workers=settings.CMS_CHART_EXPORTER_API_MAX_CONCURRENT_RENDERS) as executor:
        fetched = list(executor.map(lambda block: _fetch_chart_response(block, client), blocks))

    results = []
    for block, outcome in zip(blocks, fetched, strict=True):
        if isinstance(outcome, ChartRenderResult):
            # Nothing to do, we already have a result (either it was skipped or an error occurred)
            results.append(outcome)
            continue
        image = RenderedChartImage.objects.create_from_export_response(
            outcome.response, config_hash=outcome.config_hash
        )
        block.value["rendered_chart_image"] = image
        results.append(ChartRenderResult(block_id=block.id, changed=True))

    duration = time.monotonic() - start

    logger.info(
        "Rendered %d chart block(s) in %.2fs (%d failed)",
        len(blocks),
        duration,
        sum(1 for result in results if result.error),
    )
    return results
