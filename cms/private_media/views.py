from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.cache import add_never_cache_headers, patch_cache_control
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
        """This method immitates `wagtail.images.views.serve.ServeView.get()`, but introduces an
        additional permission check for private images, and returns responses with varied
        cache headers applied, depending on the scenario.

        NOTE: For simplicity, cache headers for 404 or 403 responses are not customised
        here. They should be controlled elsewhere (either in project settings or at the
        edge-cache provider level).
        """
        if not verify_signature(signature.encode(), image_id, filter_spec, key=self.key):
            raise SuspiciousOperation

        image = self.get_image(image_id)

        # Block access to private image if the user has insufficient permissions
        user = self.request.user
        if image.is_private and (
            not user.is_authenticated
            or not image_permission_policy.user_has_any_permission_for_instance(
                user, ["choose", "add", "change"], image
            )
        ):
            raise PermissionDenied

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

        # If there's no reason (within our control) for the file not to be served by
        # media infrastructure, redirect
        if image.is_public and not image.has_outdated_file_permissions():
            try:
                file_url = rendition.file.url
            except NotImplementedError:
                file_url = rendition.file.path
            return self.redirect_to_file(file_url)

        # Serve file contents
        if image.is_public:
            return self.serve_public_rendition(rendition)
        return self.serve_private_rendition(rendition)

    def get_image(self, image_id: int) -> "AbstractImage":
        """Return an image object matching the provided `image_id`, or raise
        a `Http404` exception if no such image exists.

        NOTE: We're not applying any specific cache headers to the response,
        because cache behaviour for 404 responses is configured elsewhere (
        either in project settings or at the edge-cache provider level).
        """
        return get_object_or_404(get_image_model(), id=image_id)

    def redirect_to_file(self, url: str) -> "HttpResponseRedirect":
        """Return a cachable temporary redirect to the requested file URL.

        The response is cached for 1 hour to reduce load on the web server.
        If the image privacy changes in the meantime, purge requests for this
        URL (and other rendition URLs) will be submitted to the active
        edge-cache provider.
        """
        response = redirect(url)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    def serve_public_rendition(self, rendition: "AbstractRendition") -> "FileResponse":
        """Return a cachable FileResponse for the requested rendition.

        The response is cached for 1 hour to reduce load on the web server.
        If the image privacy changes in the meantime, purge requests for this
        URL (and other rendition URLs) will be submitted to the active
        edge-cache provider.
        """
        response = self._serve_rendition(rendition)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    def serve_private_rendition(self, rendition: "AbstractRendition") -> "FileResponse":
        """Return a non-cachable FileResponse for the requested rendition.

        While an image is still private, access is dependant on the current
        user's permissions, so responses are not suitable for reuse.
        """
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
        """This method immitates `wagtail.documents.views.serve.serve()`, but introduces an
        additional permission check for private documents, and returns responses with varied
        cache headers applied, depending on the scenario.

        NOTE: For simplicity, cache headers for 404 or 403 responses are not customised
        here. They should be controlled elsewhere (either in project settings or at the
        edge-cache provider level).
        """
        document = self.get_document(document_id, document_filename)

        # Block access to private documents if the user has insufficient permissions
        user = self.request.user
        if document.is_private and (
            not user.is_authenticated
            or not document_permission_policy.user_has_any_permission_for_instance(
                user, ["choose", "add", "change"], document
            )
        ):
            raise PermissionDenied

        # Send document_served signal
        document_served.send(sender=type(document), instance=document, request=request)

        # If there's no reason (within our control) for the file not to be served by
        # media infrastructure, redirect
        if document.is_public and not document.has_outdated_file_permissions():
            try:
                file_url = document.file.url
            except NotImplementedError:
                file_url = document.file.path
            return self.redirect_to_file(file_url)

        # Serve file contents
        if document.is_public:
            return self.serve_public_document(document)
        return self.serve_private_document(document)

    def get_document(self, document_id: int, document_filename: str) -> "AbstractDocument":
        """Return a document object matching the provided `document_id` and
        `document_filename`, or raise a `Http404` exception if no such
        document exists.

        NOTE: We're not applying any specific cache headers to the response,
        because cache behaviour for 404 responses is configured elsewhere (
        either in project settings or at the edge-cache provider level).
        """
        obj = get_object_or_404(get_document_model(), id=document_id)
        if obj.filename != document_filename:
            raise Http404
        return obj

    def redirect_to_file(self, url: str) -> "HttpResponseRedirect":
        """Return a cachable temporary redirect to the file URL.

        The redirect response is cached for 1 hour to alleviate load on the
        the web server. If the document privacy changes in the meantime, a
        purge request for this URL will be submitted to the active edge-cache
        provider.
        """
        response = redirect(url, permanent=False)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    def serve_public_document(self, document: "AbstractDocument") -> "FileResponse":
        """Return a cachable FileResponse for the requested document file.

        The response is cached for 1 hour to reduce load on the web server.
        If the document privacy changes in the meantime, a purge requests for
        this URL will be submitted to the active edge-cache provider.
        """
        response = self._serve_document(document)
        patch_cache_control(response, max_age=3600, public=True)
        return response

    def serve_private_document(self, document: "AbstractDocument") -> "FileResponse":
        """Return a non-cachable FileResponse for the requested document file.

        While a document is still private, access is dependant on the current
        user's permissions, so responses are not suitable for reuse.
        """
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
        response["Content-Security-Policy"] = "default-src 'none'"

        # Prevent browsers from auto-detecting the content-type of a document
        response["X-Content-Type-Options"] = "nosniff"

        return response
