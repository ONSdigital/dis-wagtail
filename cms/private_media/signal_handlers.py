from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models import CharField, Exists, OuterRef
from django.db.models.functions import Cast
from django.db.models.signals import post_delete, post_save
from django.utils import timezone
from wagtail.images.models import AbstractImage
from wagtail.models import ReferenceIndex
from wagtail.signals import page_published, page_unpublished

from cms.private_media.models import MediaParentMixin
from cms.private_media.utils import get_media_parent_models, get_parent_derived_privacy_models

if TYPE_CHECKING:
    from wagtail.models import Page


def assign_unparented_child_media_on_first_save(instance: MediaParentMixin, **kwargs: Any) -> None:
    """Signal handler to be connected to the 'post_save' signal for models that inherit from
    MediaParentMixin. It is responsible for assigning missing parent_object_ids to child
    media that were uploaded for this object before it was saved for the first time.
    """
    if not kwargs.get("created", False):
        return None

    instance_ct = ContentType.objects.get_for_model(instance)
    for model_class in get_parent_derived_privacy_models():
        unparented_media = model_class.objects.filter(
            parent_object_id_outstanding=True,
            parent_object_content_type=instance_ct,
            created_at__gte=timezone.now() - timedelta(hours=2),
        )
        if owner_id := getattr(instance, "owner_id", None):
            unparented_media = unparented_media.filter(uploaded_by_user_id=owner_id)
        for obj in unparented_media:
            # Save objects individually so that the set_privacy() is triggered
            obj.parent_object_id = instance.pk
            obj.parent_object_id_outstanding = False
            obj.save()
    return None


def remove_child_media_on_delete(instance: MediaParentMixin, **kwargs: Any) -> None:
    """Signal handler to be connected to the 'pre_delete' signal for models that inherit from
    MediaParentMixin. It is responsible for removing child media that are associated with the
    object being deleted.
    """
    if kwargs.get("raw", False):
        return None

    instance_ct = ContentType.objects.get_for_model(instance)
    for model_class in get_parent_derived_privacy_models():
        model_ct = ContentType.objects.get_for_model(model_class)
        children = model_class.objects.filter(
            parent_object_content_type=model_ct, parent_object_id=instance.pk
        ).annotate(
            referenced_elsewhere=Exists(
                ReferenceIndex.objects.filter(
                    to_content_type=model_ct,
                    to_object_id=Cast(OuterRef("pk"), CharField()),
                ).exclude(content_type=instance_ct, object_id=str(instance.pk))
            )
        )

        # Delete children that are not referenced elsewhere
        children.filter(referenced_elsewhere=False).delete()

        # Set 'parent_object_deleted' for the remaining children
        children.filter(referenced_elsewhere=True).update(parent_object_deleted=True)
    return None


def publish_media_on_page_publish(instance: "Page", **kwargs: Any) -> None:
    """Signal handler to be connected to the 'page_published' signal for
    all page types. It is responsible for identifying any privacy-controlled
    media used by the page, and ensuring that it is also made public.
    """
    if not isinstance(instance, MediaParentMixin):
        return None

    for model_class in get_parent_derived_privacy_models():
        queryset = model_class.objects.filter(
            is_private=True, parent_object_content_type=instance.cached_content_type, parent_object_id=instance.id
        )
        if issubclass(model_class, AbstractImage):
            queryset = queryset.prefetch_related("renditions")
        if hasattr(model_class.objects, "bulk_make_public"):
            model_class.objects.bulk_make_public(queryset)
        else:
            raise ImproperlyConfigured(
                f"The default manager for {model_class.__name__} does not have a 'bulk_make_private' method."
            )

    return None


def unpublish_media_on_page_unpublish(instance: "Page", **kwargs: Any) -> None:
    """Signal handler to be connected to the 'page_unpublished' signal for
    all page types. It is responsible for identifying any privacy-controlled
    media used exclusively by the page, and ensuring that it is also made
    private.
    """
    if not isinstance(instance, MediaParentMixin):
        return None

    for model_class in get_parent_derived_privacy_models():
        queryset = model_class.objects.filter(
            is_private=False, parent_object_content_type=instance.cached_content_type, parent_object_id=instance.id
        )
        if issubclass(model_class, AbstractImage):
            queryset = queryset.prefetch_related("renditions")
        queryset = queryset.annotate(
            is_referenced_elsewhere=Exists(
                ReferenceIndex.objects.filter(
                    to_content_type=ContentType.objects.get_for_model(model_class),
                    to_object_id=Cast(OuterRef("pk"), output_field=CharField()),
                ).exclude(content_type=instance.cached_content_type, object_id=str(instance.id))
            )
        ).filter(is_referenced_elsewhere=False)
        if hasattr(model_class.objects, "bulk_make_private"):
            model_class.objects.bulk_make_private(queryset)
        else:
            raise ImproperlyConfigured(
                f"The default manager for {model_class.__name__} does not have a 'bulk_make_private' method."
            )
    return None


def register_signal_handlers() -> None:
    """Register signal handlers for models using the private media system."""
    page_published.connect(publish_media_on_page_publish, dispatch_uid="publish_media")
    page_unpublished.connect(unpublish_media_on_page_unpublish, dispatch_uid="unpublish_media")
    for model_class in get_media_parent_models():
        post_save.connect(
            assign_unparented_child_media_on_first_save, sender=model_class, dispatch_uid="assign_unparented_media"
        )
        post_delete.connect(remove_child_media_on_delete, sender=model_class, dispatch_uid="remove_child_media")
