from django.urls import path

from cms.images.views import ImageDownloadView

urlpatterns = [
    path("images/download/<int:rendition_id>", ImageDownloadView.as_view(), name="image_download"),
]
