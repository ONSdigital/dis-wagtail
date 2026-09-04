import logging
import os
import uuid
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models
from django.urls import reverse

from cms.private_media.managers import PrivateDocumentManager
from cms.private_media.models import PrivateDocumentMixin

if TYPE_CHECKING:
    from cms.datavis.clients.chart_exporter import ChartObjectResponse

logger = logging.getLogger(__name__)


class RenderedChartImageManager(PrivateDocumentManager):
    def create_from_export_response(self, response: ChartObjectResponse, *, config_hash: str) -> RenderedChartImage:
        """Create an instance from a chart exporter API response.

        The exporter has already written the file to S3, so we point the FieldFile at the
        existing key rather than uploading anything ourselves.
        """
        if response.bucket != settings.AWS_STORAGE_BUCKET_NAME:
            # ACL toggling resolves the object against the configured bucket, not the
            # response's, so a mismatch here means privacy changes would silently target
            # the wrong bucket.
            logger.error(
                "Chart exporter response bucket '%s' does not match configured bucket '%s' for export id '%s'",
                response.bucket,
                settings.AWS_STORAGE_BUCKET_NAME,
                response.id,
            )

        instance = RenderedChartImage(
            export_id=uuid.UUID(response.id),
            config_hash=config_hash,
            width=response.width,
            height=response.height,
            content_type=response.content_type,
            size_bytes=response.size_bytes,
        )
        instance.file.name = response.key
        instance.save()
        return instance


class RenderedChartImage(PrivateDocumentMixin, models.Model):
    """Metadata for a chart image rendered and stored privately by the chart exporter service.

    One instance represents a single rendered chart. The exporter writes the PNG directly to
    S3; this model only stores a reference to it, plus the config hash used to detect and skip
    re-rendering of unchanged charts.
    """

    file = models.FileField(upload_to="rendered_charts")
    export_id = models.UUIDField(unique=True)
    config_hash = models.CharField(max_length=64, db_index=True)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects: ClassVar[RenderedChartImageManager] = RenderedChartImageManager()

    def __str__(self) -> str:
        return self.filename

    @property
    def filename(self) -> str:  # type: ignore[override]
        return os.path.basename(self.file.name or "")

    @property
    def serve_url(self) -> str:
        return reverse("rendered_chart_image_serve", args=[self.pk])
