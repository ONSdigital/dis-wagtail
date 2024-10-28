from django.db import models
from wagtail.images.models import AbstractImage, AbstractRendition, Image


class CustomImage(AbstractImage):
    """Custom Wagtail image class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """

    admin_form_fields = Image.admin_form_fields


class Rendition(AbstractRendition):
    """Our custom rendition class."""

    image = models.ForeignKey(  # type: ForeignKey["CustomImage"]
        "CustomImage", related_name="renditions", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
