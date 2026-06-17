from django.urls import path

from .views import unlock

app_name = "workflows"
urlpatterns = [
    path(
        "pages/<int:page_id>/unlock/",
        unlock,
        name="unlock",
    ),
]
