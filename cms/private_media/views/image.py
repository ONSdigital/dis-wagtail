from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from wagtail.images.permissions import permission_policy
from wagtail.images.views.chooser import ImageChooseView as WagtailImageChooseView
from wagtail.images.views.chooser import viewset as chooser_viewset
from wagtail.images.views.serve import ServeView

from cms.private_media.views.mixins import ParentIdentifyingChooserViewMixin

if TYPE_CHECKING:
    from django.http import HttpResponse

    from cms.private_media.models import AbstractPrivateImage, AbstractPrivateRendition


class ImageChooseView(ParentIdentifyingChooserViewMixin, WagtailImageChooseView):
    """A replacement for Wagtail's ImageChooseView that identifies the
    'parent object' from the 'parent_url' query parameter, and uses it
    to populate hidden field values in the 'creation' form.
    """

    @classmethod
    def as_view(cls, **kwargs: Any) -> Callable[..., "HttpResponse"]:
        """Wagtail's version of this view is modified quite heavily by the "ImageChooserViewSet"
        instance before it is actually registered. This override mimics some of that by retreiving
        some of those overrides from the viewset instance and applying them here.
        """
        _kwargs = chooser_viewset.get_common_view_kwargs()
        _kwargs.update(kwargs)
        _kwargs.pop("per_page")
        view: Callable[..., HttpResponse] = super().as_view(**_kwargs)
        return view


class PrivateImageServeView(ServeView):
    def serve(self, rendition: "AbstractPrivateRendition") -> "HttpResponse":
        image: AbstractPrivateImage = rendition.image

        # If there's no reason (within our control) for the file not to be served by
        # media infrastructure, redirect
        if image.is_public and image.file_permissions_are_up_to_date():
            return redirect(rendition.file.url)

        # Block access to private images if the user has insufficient permissions
        user = self.request.user
        if image.is_private and (
            not user.is_authenticated
            or not permission_policy.user_has_any_permission_for_instance(user, ["choose", "add", "change"], image)
        ):
            raise PermissionDenied

        # Serve the file until it is no longer private, or file permissions
        # have been set successfully
        response: HttpResponse = super().serve(rendition)
        return response
