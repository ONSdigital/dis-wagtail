import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cms.core.blocks.constants import CHART_BLOCK_TYPES
from cms.datavis.clients.chart_exporter import (
    ChartExporterClient,
    ChartExporterError,
    ChartExporterMalformedRequest,
    ChartExporterUnavailable,
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


def iter_chart_blocks(value: StreamValue | None) -> Iterator[StreamChild]:
    """Recursively yield chart blocks from a StreamValue, including those nested in sections."""
    if not value:
        return
    for block in value:
        if block.block_type == "section":
            yield from iter_chart_blocks(block.value.get("content"))
        elif block.block_type in CHART_BLOCK_TYPES:
            yield block


def _render_chart_block(block: StreamChild, client: ChartExporterClient) -> ChartRenderResult:
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

    image = RenderedChartImage.objects.create_from_export_response(response, config_hash=config_hash)
    block.value["rendered_chart_image"] = image
    return ChartRenderResult(block_id=block.id, changed=True)


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
    results = [_render_chart_block(block, client) for block in blocks]
    duration = time.monotonic() - start

    logger.info(
        "Rendered %d chart block(s) in %.2fs (%d failed)",
        len(blocks),
        duration,
        sum(1 for result in results if result.error),
    )
    return results
