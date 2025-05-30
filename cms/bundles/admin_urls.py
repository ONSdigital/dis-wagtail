from django.urls import path

from .views.add_to_bundle import AddToBundleView
from .views.preview import PreviewBundleReleaseCalendarView, PreviewBundleView

app_name = "bundles"
urlpatterns = [
    path("add/<int:page_to_add_id>/", AddToBundleView.as_view(), name="add_to_bundle"),
    path("preview/<int:bundle_id>/page/<int:page_id>/", PreviewBundleView.as_view(), name="preview"),
    path(
        "preview/<int:bundle_id>/release_calendar/",
        PreviewBundleReleaseCalendarView.as_view(),
        name="preview_release_calendar",
    ),
]
