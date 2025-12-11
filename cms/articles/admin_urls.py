from django.urls import path

from .views import RevisionChartDownloadView

app_name = "articles"
urlpatterns = [
    path(
        "pages/<int:page_id>/revisions/<int:revision_id>/download-chart/<str:chart_id>/",
        RevisionChartDownloadView.as_view(),
        name="revision_chart_download",
    ),
]
