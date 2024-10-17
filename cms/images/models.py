from django.db import models
from wagtail.images.models import AbstractImage, AbstractRendition, Image


class CustomImage(AbstractImage):
    admin_form_fields = Image.admin_form_fields


class Rendition(AbstractRendition):
    image = models.ForeignKey("CustomImage", related_name="renditions", on_delete=models.CASCADE)

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
