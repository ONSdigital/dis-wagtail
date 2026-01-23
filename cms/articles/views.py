# Re-exports for backwards compatibility
from cms.core.views import (
    RevisionChartDownloadView,
    RevisionTableDownloadView,
    get_csv_data_from_chart,
    get_csv_data_from_table,
    get_revision_page_for_request,
    user_can_access_csv_download,
)

__all__ = [
    "RevisionChartDownloadView",
    "RevisionTableDownloadView",
    "get_csv_data_from_chart",
    "get_csv_data_from_table",
    "get_revision_page_for_request",
    "user_can_access_csv_download",
]
