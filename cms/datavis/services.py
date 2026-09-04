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
    from wagtail.models import Page

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


def render_charts_for_page(page: Page) -> list[ChartRenderResult]:
    """Render (or reuse) chart images for every chart block on the page's latest revision.

    Saves a new revision when any image changed, so the result is carried by a subsequent
    publish. Operates on the latest revision's content rather than the live page, since this
    is called ahead of a page being submitted for review, before it may ever be published.
    """
    revision_page = page.get_latest_revision_as_object()
    field_names = getattr(type(revision_page).base_form_class, "protected_chart_image_fields", ())
    blocks = [
        block for field_name in field_names for block in iter_chart_blocks(getattr(revision_page, field_name, None))
    ]

    results = render_chart_blocks(blocks)
    if any(result.changed for result in results):
        revision_page.save_revision(log_action=False)
    return results
