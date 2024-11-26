from django.db import models
from wagtail.images.models import AbstractImage

from cms.private_media.models import PrivateAbstractRendition, PrivateImageMixin


class CustomImage(PrivateImageMixin, AbstractImage):
    """Custom Wagtail image class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """
    pass


class Rendition(PrivateAbstractRendition):
    """Our custom rendition class."""

    image = models.ForeignKey["CustomImage"]("CustomImage", related_name="renditions", on_delete=models.CASCADE)

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
