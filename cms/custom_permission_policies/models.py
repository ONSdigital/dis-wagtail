import logging
from typing import ClassVar

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from wagtail.documents.models import Document
from wagtail.images.models import Image

logger = logging.getLogger(__name__)


class MediaParentMixin(models.Model):
    """A mixin for models that can be considered 'parents' of media objects that
    make use of `MediaChildMixin`.
    """

    class Meta:
        abstract = True


class MediaChildMixin(models.Model):
    """A mixin for models where individual instances can be considered as 'children' of a parent object
    (e.g. a Wagtail Page).
    """

    parent_object_content_type = models.ForeignKey(
        "contenttypes.ContentType", null=True, blank=True, on_delete=models.CASCADE
    )
    parent_object_id = models.PositiveIntegerField(null=True, blank=True)
    parent_object = GenericForeignKey("parent_object_content_type", "parent_object_id")
    parent_object_id_outstanding = models.BooleanField(default=False, blank=True)
    parent_object_deleted = models.BooleanField(default=False, editable=False)

    class Meta:
        abstract = True


class ChildImageMixin(MediaChildMixin):
    """A version of `MediaChildMixin` to be used with custom Wagtail image models."""

    # This override is necessary to include the parent-object-related
    # fields in the Wagtail admin form as hidden fields
    admin_form_fields: ClassVar[list[str]] = [
        *Image.admin_form_fields,
        "parent_object_id",
        "parent_object_content_type",
        "parent_object_id_outstanding",
    ]

    class Meta:
        abstract = True


class ChildDocumentMixin(MediaChildMixin):
    """A version of `MediaChildMixin` to be used with custom Wagtail document models."""

    # This override is necessary to include the parent-object-related
    # fields in the Wagtail admin form as hidden fields
    admin_form_fields: ClassVar[list[str]] = [
        *Document.admin_form_fields,
        "parent_object_id",
        "parent_object_content_type",
        "parent_object_id_outstanding",
    ]

    class Meta:
        abstract = True
