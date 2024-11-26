import logging
from collections.abc import Iterator
from enum import StrEnum
from typing import Any, ClassVar

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import File
from django.db import models
from django.db.models.fields.files import FieldFile
from django.db.models.functions import Cast
from django.utils import timezone
from wagtail.documents import get_document_model
from wagtail.documents.models import Document, DocumentQuerySet
from wagtail.images import get_image_model
from wagtail.images.models import AbstractRendition, Filter, Image, ImageQuerySet
from wagtail.models import ReferenceIndex

from cms.private_media import utils
from cms.private_media.manager import PrivateFilesModelManager

logger = logging.getLogger(__name__)


class Privacy(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"


class PrivateFilesMixin(models.Model):
    """A mixin class for models that has files that need to remain private
    until the object itself is no longer private.

    Subclasses must implement the `determine_privacy()` method, which should
    return a `Privacy` value to determine the correct value for the `is_private`
    field (and by extension, whether files should be made private or public).

    Subclasses must implement the `get_privacy_controlled_files()` method,
    which should return an iterator of `FieldFile` objects that are managed
    by the model instance.

    Where individual objects are updated (usually via the Wagtail UI), changes to
    managed field values are written to the database by the overridden
    `save()` method.

    Where multiple objects are updated at once (e.g. via a signal handler or
    management command running on the server), changes to managed field values
    are written to the database by the bulk update methods provided by
    `PrivateFilesModelManager`.
    """

    is_private = models.BooleanField(default=False, editable=False)
    privacy_last_changed = models.DateTimeField(null=True, editable=False)
    file_permissions_last_set = models.DateTimeField(null=True, editable=False)

    class Meta:
        abstract = True

    objects = PrivateFilesModelManager()

    def save(self, *args: Any, set_file_permissions: bool = True, **kwargs: Any) -> None:
        # Set managed field values
        self.set_privacy()
        # Save model field changes at this point
        super().save(*args, **kwargs)

        # Trigger file permission updates after-the-fact
        if set_file_permissions and (
            self.file_permissions_last_set is None
            or (self.privacy_last_changed and self.file_permissions_last_set < self.privacy_last_changed)
        ):
            results = utils.bulk_set_file_permissions(self.get_privacy_controlled_files(), self.is_private)
            # Only update 'file_permissions_last_set' if all updates were successfull
            if set(results.values()) == {True}:
                self.file_permissions_last_set = timezone.now()
                kwargs["update_fields"] = ["file_permissions_last_set"]
                super().save(*args, **kwargs)

    @property
    def is_public(self) -> bool:
        return not self.is_private

    def file_permissions_are_up_to_date(self) -> bool:
        if self.privacy_last_changed is None:
            return True
        if self.file_permissions_last_set is None:
            return False
        return self.file_permissions_last_set > self.privacy_last_changed

    def determine_privacy(self) -> Privacy:
        raise NotImplementedError

    def set_privacy(self) -> bool:
        was_private = self.is_private
        privacy_changed = False

        self.is_private = self.determine_privacy() == Privacy.PRIVATE
        privacy_changed = self.is_private != was_private
        if not self.pk or privacy_changed:
            self.privacy_last_changed = timezone.now()
        return privacy_changed

    def get_privacy_controlled_files(self) -> Iterator[FieldFile]:
        raise NotImplementedError


class MediaParentMixin(models.Model):
    """A mixin for models that can be considered 'parents' of media objects that
    make use of `MediaChildMixin`.
    """

    class Meta:
        abstract = True

    @classmethod
    def get_child_media_models(self) -> Iterator[type[models.Model]]:
        image_model = get_image_model()
        if issubclass(image_model, MediaChildMixin):
            yield image_model

        document_model = get_document_model()
        if issubclass(document_model, MediaChildMixin):
            yield document_model

        return None

    def save(self, *args: Any, **kwargs: Any) -> None:
        is_new = not self.pk
        super().save(*args, **kwargs)
        this_content_type = ContentType.objects.get_for_model(self)
        if is_new:
            # Set missing 'parent_object_ids' for media that is likley to have been
            # uploaded for this object before it was saved for the first time
            for model in self.get_child_media_models():
                qs = model.objects.filter(
                    parent_object_id_outstanding=True,
                    parent_object_content_type=this_content_type,
                    created_at__gte=timezone.now() - timezone.timedelta(hours=2),
                )
                if getattr(self, "owner_id", None):
                    qs = qs.filter(uploaded_by_user_id=self.owner_id)
                qs.update(
                    parent_object_id=self.pk,
                    parent_object_id_outstanding=False,
                )

    def delete(self, *args, **kwargs) -> None:
        super().delete(*args, **kwargs)
        this_content_type = ContentType.objects.get_for_model(self)
        for model in self.get_child_media_models():
            # Upate 'media children' for this object
            content_type = ContentType.objects.get_for_model(model)
            referenced_elsewhere_query = ReferenceIndex.objects.filter(
                to_content_type=content_type,
                to_object_id=Cast(models.OuterRef("pk"), models.CharField(max_length=255)),
            ).exclude(content_type=this_content_type, object_id=str(self.pk))
            for obj in (
                model.objects.filter(parent_object_id=self.pk)
                .annotate(referenced_elsewhere=models.Exists(referenced_elsewhere_query))
            ):
                if not obj.referenced_elsewhere:
                    obj.delete()
                else:
                    obj.parent_object_deleted = True
                    obj.save(update_fields=["parent_object_deleted"])


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

    def parent_object_is_not_live(self) -> bool:
        if self.parent_object_id_outstanding:
            return True
        if not self.parent_object_id:
            return False
        if self.parent_object_deleted:
            return True
        return not self.parent_object.live


class ParentDerivedPrivacyMixin(PrivateFilesMixin, MediaChildMixin):
    """A mixin class that combines `PrivateFilesMixin` and `MediaChildMixin`,
    to determine the object's privacy based on whether the parent object is live.
    """

    class Meta:
        abstract = True

    def determine_privacy(self) -> Privacy:
        return Privacy.PRIVATE if self.parent_object_is_not_live() else Privacy.PUBLIC


class PrivateImageManager(PrivateFilesModelManager):
    """A subclass of `PrivateFilesModelManager` that returns instances of
    Wagtail's custom `ImageQuerySet`, which includes image-specific
    filter methods other functionality that Wagtail itself depends on.
    """

    def get_queryset(self) -> ImageQuerySet:
        return ImageQuerySet(self.model, using=self._db)


class PrivateImageMixin(ParentDerivedPrivacyMixin):
    """A mixin class to be applied to a project's custom Image model,
    allowing the privacy to be controlled effectively, depending on the
    status of the parent object.
    """

    objects = PrivateImageManager()

    # This override is necessary to include the parent-object-related
    # fields in the Wagtail admin form as hidden fields
    admin_form_fields: ClassVar[list[str]] = [
        *Image.admin_form_fields,
        "parent_object_id",
        "parent_object_content_type",
        "parent_object_id_outstanding"
    ]

    class Meta:
        abstract = True

    def get_privacy_controlled_files(self) -> Iterator[File]:
        if self.file:
            yield self.file
        for rendition in self.renditions.all():
            yield rendition.file

    def create_renditions(self, *filters: Filter) -> dict[Filter, AbstractRendition]:
        created_renditions = super().create_renditions(*filters)
        files = [r.file for r in created_renditions]
        utils.bulk_set_file_permissions(files, self.is_private)
        return created_renditions


class PrivateAbstractRendition(AbstractRendition):
    """A replacement for Wagtail's built-in `AbstractRendition` model, that should be used as
    a base for rendition models for image models subclassing `PrivateImageMixin`. This
    is necessary to ensure that only users with relevant permissions can view renditions
    for private images.
    """

    class Meta:
        abstract = True

    @staticmethod
    def construct_cache_key(image, filter_cache_key, filter_spec):
        """Overrides the implementation from AbstractRendition to include an
        indication of whether the image is private or not.
        """
        return "wagtail-rendition-" + "-".join(
            [
                str(image.id),
                image.file_hash,
                str(image.is_private),
                filter_cache_key,
                filter_spec,
            ]
        )

    @property
    def url(self) -> str:
        """For private images, or images that haven't yet had their file
        permissions set succesfully, redirect users to a view that is capable
        of checking permissions and serving the file.

        For public images that have had their file permissions set successfully,
        return the file URL, so that S3 (or other active storage backend)
        handles the request.
        """
        from wagtail.images.views.serve import generate_image_url  # pylint: disable=import-outside-toplevel

        if self.image.is_public and self.image.file_permissions_are_up_to_date():
            return self.file.url
        return generate_image_url(self.image, self.filter_spec)


class PrivateDocumentManager(PrivateFilesModelManager):
    """A subclass of `PrivateFilesModelManager` that returns instances of
    Wagtail's custom `DocumentQuerySet`, which includes document-specific
    filter methods other functionality that Wagtail itself depends on.
    """

    def get_queryset(self) -> DocumentQuerySet:
        return DocumentQuerySet(self.model, using=self._db)


class PrivateDocumentMixin(ParentDerivedPrivacyMixin):
    """A mixin class to be applied to a project's custom Document model,
    allowing the privacy to be controlled effectively, depending on the
    collection the image belongs to.
    """

    # This override is necessary to include the parent-object-related
    # fields in the Wagtail admin form as hidden fields
    admin_form_fields: ClassVar[list[str]] = [
        *Document.admin_form_fields,
        "parent_object_id",
        "parent_object_content_type",
        "parent_object_id_outstanding"
    ]

    objects = PrivateDocumentManager()

    class Meta:
        abstract = True

    def get_privacy_controlled_files(self) -> Iterator[FieldFile]:
        if self.file:
            yield self.file
