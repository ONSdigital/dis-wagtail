import logging
from typing import TYPE_CHECKING, Any, ClassVar

from django.core.exceptions import ImproperlyConfigured

from cms.datavis.services import iter_chart_blocks, render_chart_blocks

if TYPE_CHECKING:
    from collections.abc import Iterator

    from wagtail.blocks.stream_block import StreamChild
    from wagtail.models import Revision

logger = logging.getLogger(__name__)


class ChartImageRenderMixin:
    """Pre-renders chart fallback images whenever a revision is saved.

    This is best effort: a failed render is logged and leaves whatever image is already
    attached in place, so an exporter outage never stops an editor saving their work. The
    guarantee that images are present and current comes from
    ``PageWithProtectedChartImagesAdminForm``, which renders synchronously and blocks
    submission for review on failure. A bundle can only be approved once every bundled page
    has passed through that gate, via its own workflow reaching a review task, so nothing
    further is needed at the bundle level.

    ``chart_image_fields`` also drives the tamper protection in
    ``PageWithProtectedChartImagesAdminForm``, so both must be applied to the same page model.
    """

    chart_image_fields: ClassVar[tuple[str, ...]] = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.chart_image_fields:
            raise ImproperlyConfigured(f"{cls.__name__} must define chart_image_fields")

    def get_chart_blocks(self) -> Iterator[StreamChild]:
        for field_name in self.chart_image_fields:
            yield from iter_chart_blocks(getattr(self, field_name, None))

    def save_revision(self, *args: Any, **kwargs: Any) -> Revision:
        try:
            render_chart_blocks(self.get_chart_blocks())
        except Exception:  # pylint: disable=broad-exception-caught
            # Saving must never fail because of the exporter, so nothing may escape here.
            logger.exception(
                "Could not pre-render chart images",
                extra={"page_id": self.pk},  # type: ignore[attr-defined]
            )

        return super().save_revision(*args, **kwargs)  # type: ignore[misc]
