import os
from typing import TYPE_CHECKING

from django.http import FileResponse, Http404
from django.views import View

from cms.images.models import Rendition

if TYPE_CHECKING:
    from django.http import HttpRequest


class ImageDownloadView(View):
    def get(self, request: HttpRequest, rendition_id: int) -> FileResponse:
        try:
            rendition = Rendition.objects.select_related("image").get(pk=rendition_id)
        except Rendition.DoesNotExist as exc:
            raise Http404 from exc

        _, ext = os.path.splitext(rendition.file.name)
        filename = f"{rendition.image.title}{ext}"

        return FileResponse(rendition.file.open("rb"), as_attachment=True, filename=filename)
