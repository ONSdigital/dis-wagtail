from collections.abc import Iterator
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import Any

import stamina
from django.conf import settings
from django.test import override_settings

from cms.datavis.tests.chart_exporter_mock import DEFAULT_BUCKET, ChartExporterMock


@contextmanager
def mock_chart_exporter(**kwargs: Any) -> Iterator[ChartExporterMock]:
    """Run a ChartExporterMock and point the CMS's chart exporter client at it.

    The mock writes rendered PNGs to a temporary MEDIA_ROOT, so chart images can be served, and
    returns the configured bucket. Retries keep the client's own number of attempts, but without
    stamina's backoff waits. Keyword arguments are passed on to ChartExporterMock.

    In a test case: ``cls.chart_exporter = cls.enterClassContext(mock_chart_exporter())``, then
    ``self.chart_exporter.reset()`` in ``setUp``.
    """
    with TemporaryDirectory() as media_root:
        options = {
            "bucket": getattr(settings, "AWS_STORAGE_BUCKET_NAME", DEFAULT_BUCKET),
            "output_dir": media_root,
            **kwargs,
        }
        with (
            ChartExporterMock(**options) as mock,
            override_settings(
                MEDIA_ROOT=media_root,
                CMS_CHART_EXPORTER_API_ENABLED=True,
                CMS_CHART_EXPORTER_API_BASE_URL=mock.url,
                CMS_CHART_EXPORTER_API_TIMEOUT_SECONDS=5,
            ),
            stamina.set_testing(True, attempts=100, cap=True),
        ):
            yield mock
