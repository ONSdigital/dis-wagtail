from django.shortcuts import redirect
from wagtail.images.views.serve import ServeView


class ImageServeView(ServeView):
    def serve(self, rendition):
        # If there's no reason (within our control) for the file not to be served by S3, redirect
        if rendition.image.is_public and rendition.image.acls_are_up_to_date():
            return redirect(rendition.file.url)
        # Serve the file until it is no longer private, or ACLs have been updated successfully
        return super().serve(rendition)
