from collections.abc import Sequence
from typing import ClassVar

from django.db import models
from wagtail.images.models import AbstractImage, Image

from cms.private_media.models import AbstractPrivateRendition, PrivateImageMixin


class CustomImage(PrivateImageMixin, AbstractImage):  # type: ignore[django-manager-missing]
    """Custom Wagtail image class.

    Using a custom class from the beginning allows us to add
    any customisations we may need.
    """

    admin_form_fields: ClassVar[Sequence[str]] = Image.admin_form_fields


class Rendition(AbstractPrivateRendition):
    """Our custom rendition class."""

    image = models.ForeignKey(  # type: ignore[var-annotated]
        "CustomImage", related_name="renditions", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
