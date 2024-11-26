from django.db import models

from cms.private_media.models import AbstractPrivateImage, AbstractPrivateRendition


class CustomImage(AbstractPrivateImage):  # type: ignore[django-manager-missing]
    """Custom Wagtail image class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """


class Rendition(AbstractPrivateRendition):
    """Our custom rendition class."""

    image = models.ForeignKey(  # type: ignore[var-annotated]
        "CustomImage", related_name="renditions", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
