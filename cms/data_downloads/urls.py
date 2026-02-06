from django.urls import path

from .views import RevisionChartDownloadView, RevisionTableDownloadView

app_name = "data_downloads"
urlpatterns = [
    path(
        "pages/<int:page_id>/revisions/<int:revision_id>/download-chart/<str:chart_id>/",
        RevisionChartDownloadView.as_view(),
        name="revision_chart_download",
    ),
    path(
        "pages/<int:page_id>/revisions/<int:revision_id>/download-table/<str:table_id>/",
        RevisionTableDownloadView.as_view(),
        name="revision_table_download",
    ),
]
