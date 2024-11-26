from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from wagtail.images.permissions import permission_policy
from wagtail.images.views.serve import ServeView


class ImageServeView(ServeView):
    def serve(self, rendition):
        # If there's no reason (within our control) for the file not to be served by
        # media infrastructure, redirect
        if (
            rendition.image.is_public
            and rendition.image.file_permissions_are_up_to_date()
        ):
            return redirect(rendition.file.url)

        # Block access to private images if the user has insufficient permissions
        user = self.request.user
        if rendition.image.is_private and (
            not user.is_authenticated
            or not permission_policy.user_has_any_permission_for_instance(
                user, ["choose", "add", "change"], rendition.image
            )
        ):
            raise PermissionDenied

        # Serve the file until it is no longer private, or file permissions
        # have been set successfully
        return super().serve(rendition)
