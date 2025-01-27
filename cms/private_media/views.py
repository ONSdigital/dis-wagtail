from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.cache import add_never_cache_headers, patch_cache_control
from django.utils.decorators import method_decorator
from django.views.decorators.http import etag
from django.views.generic import View
from wagtail.documents import get_document_model
from wagtail.documents.models import document_served
from wagtail.documents.permissions import permission_policy as document_permission_policy
from wagtail.images import get_image_model
from wagtail.images.exceptions import InvalidFilterSpecError
from wagtail.images.models import SourceImageIOError
from wagtail.images.permissions import permission_policy as image_permission_policy
from wagtail.images.utils import verify_signature

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponseBase, HttpResponseRedirect
    from wagtail.documents.models import AbstractDocument
    from wagtail.images.models import AbstractImage, AbstractRendition


def document_etag(document: "AbstractDocument") -> str:
    return document.file_hash or ""


class ImageServeView(View):
    http_method_names: Sequence[str] = ["get"]
    key = None

    def get(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        request: "HttpRequest",
        signature: str,
        image_id: int,
        filter_spec: str,
        filename: str | None = None,  # pylint: disable=unused-argument
    ) -> "HttpResponseBase":
        if not verify_signature(signature.encode(), image_id, filter_spec, key=self.key):
            raise PermissionDenied

        image = self.get_image(image_id)

        # Block access to private image if the user has insufficient permissions
        user = self.request.user
        if image.is_private and (
            not user.is_authenticated
            or not image_permission_policy.user_has_any_permission_for_instance(
                user, ["choose", "add", "change"], image
            )
        ):
            return HttpResponse("Insufficient permissions", content_type="text/plain", status=403)

        # Get/generate the rendition
        try:
            rendition = image.get_rendition(filter_spec)
        except SourceImageIOError:
            return HttpResponse("Source image file not found", content_type="text/plain", status=410)
        except InvalidFilterSpecError:
            return HttpResponse(
                "Invalid filter spec: " + filter_spec,
                content_type="text/plain",
                status=400,
            )

        try:
            direct_url = rendition.file.url
        except NotImplementedError:
            direct_url = None

        # If there's no reason (within our control) for the file not to be served by
        # media infrastructure, redirect
        if direct_url and image.is_public and not image.has_outdated_file_permissions():
            return self.redirect_to_file(direct_url)

        # Serve file contents
        if image.is_public:
            return self.serve_public_rendition(rendition)
        return self.serve_private_rendition(rendition)

    def get_image(self, image_id: int) -> "AbstractImage":
        return get_object_or_404(get_image_model(), id=image_id)

    def redirect_to_file(self, url: str) -> "HttpResponseRedirect":
        response = redirect(url)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    def serve_public_rendition(self, rendition: "AbstractRendition") -> "FileResponse":
        response = self._serve_rendition(rendition)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    def serve_private_rendition(self, rendition: "AbstractRendition") -> "FileResponse":
        response = self._serve_rendition(rendition)
        add_never_cache_headers(response)
        return response

    def _serve_rendition(self, rendition: "AbstractRendition") -> "FileResponse":
        with rendition.get_willow_image() as willow_image:
            mime_type = willow_image.mime_type

        # Serve the file
        rendition.file.open("rb")
        response = FileResponse(rendition.file, content_type=mime_type)

        # Add a CSP header to prevent inline execution
        response["Content-Security-Policy"] = "default-src 'none'"

        # Prevent browsers from auto-detecting the content-type
        response["X-Content-Type-Options"] = "nosniff"

        return response


class DocumentServeView(View):
    http_method_names: Sequence[str] = ["get"]

    def get(self, request: "HttpRequest", document_id: int, document_filename: str) -> "HttpResponseBase":
        document = self.get_document(document_id, document_filename)

        # Block access to private documents if the user has insufficient permissions
        user = self.request.user
        if document.is_private and (
            not user.is_authenticated
            or not document_permission_policy.user_has_any_permission_for_instance(
                user, ["choose", "add", "change"], document
            )
        ):
            return HttpResponse("Insufficient permissions", content_type="text/plain", status=403)

        # Send document_served signal
        document_served.send(sender=type(document), instance=document, request=request)

        try:
            direct_url = document.file.url
        except NotImplementedError:
            direct_url = None

        # If there's no reason (within our control) for the file not to be served by
        # media infrastructure, redirect
        if direct_url and document.is_public and not document.has_outdated_file_permissions():
            return self.redirect_to_file(direct_url)

        # Serve file contents
        if document.is_public:
            return self.serve_public_document(document)
        return self.serve_private_document(document)

    def get_document(self, document_id: int, document_filename: str) -> "AbstractDocument":
        obj = get_object_or_404(get_document_model(), id=document_id)
        # Ensure that the document filename provided in the URL matches the one associated with the
        # considered document_id. If not we can't be sure that the document the user wants to
        # access is the one corresponding to the <document_id, document_filename> pair.
        if obj.filename != document_filename:
            raise Http404
        return obj

    def redirect_to_file(self, url: str) -> "HttpResponseRedirect":
        response = redirect(url)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    @method_decorator(etag(document_etag))
    def serve_public_document(self, document: "AbstractDocument") -> "FileResponse":
        response = self._serve_document(document)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    def serve_private_document(self, document: "AbstractDocument") -> "FileResponse":
        response = self._serve_document(document)
        add_never_cache_headers(response)
        return response

    def _serve_document(self, document: "AbstractDocument") -> "FileResponse":
        document.file.open("rb")
        response = FileResponse(document.file, document.content_type)

        # set filename and filename* to handle non-ascii characters in filename
        # see https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition
        response["Content-Disposition"] = document.content_disposition

        response["Content-Length"] = document.file.size

        # Add a CSP header to prevent inline execution
        if getattr(settings, "WAGTAILDOCS_BLOCK_EMBEDDED_CONTENT", True):
            response["Content-Security-Policy"] = "default-src 'none'"

        # Prevent browsers from auto-detecting the content-type of a document
        response["X-Content-Type-Options"] = "nosniff"

        return response
