from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, Exists, IntegerField, OuterRef
from django.db.models.functions import Cast
from django.db.models.signals import post_delete, post_save
from django.utils import timezone
from wagtail.models import ReferenceIndex

from cms.custom_permission_policies.models import MediaParentMixin
from cms.custom_permission_policies.utils import get_media_child_models, get_media_parent_models

if TYPE_CHECKING:
    pass


def assign_unparented_media_post_save(instance: MediaParentMixin, **kwargs: Any) -> None:
    """Signal handler to be connected to the 'post_save' signal for models that inherit from
    MediaParentMixin. It is responsible for assigning missing parent_object_ids to child
    media that were uploaded for this object before it was saved for the first time (where
    the ID of the parent object is not yet known).
    """
    instance_ct = ContentType.objects.get_for_model(instance)
    for model_class in get_media_child_models():
        if kwargs.get("created", False):
            unparented_media = model_class.objects.filter(
                parent_object_id_outstanding=True,
                parent_object_content_type=instance_ct,
                created_at__gte=timezone.now() - timedelta(hours=1),
            )
            if owner_id := getattr(instance, "owner_id", None):
                unparented_media = unparented_media.filter(uploaded_by_user_id=owner_id)
        else:
            # Comb the reference index for any media not previously parented to this page.
            # We only do this on subsequent saves, because the reference index is unlikley
            # to be populated first time round
            model_ct = ContentType.objects.get_for_model(model_class)
            unparented_media = model_class.objects.filter(
                parent_object_id_outstanding=True,
                parent_object_content_type=instance_ct,
                id__in=ReferenceIndex.objects.get_references_for_object(instance)
                .filter(
                    to_content_type=model_ct,
                )
                .annotate(id_int=Cast("to_object_id", output_field=IntegerField()))
                .values_list("id_int", flat=True),
            )
        # Update unparented media
        unparented_media.update(parent_object_id=instance.pk, parent_object_id_outstanding=False)


def update_child_media_on_delete(instance: MediaParentMixin, **kwargs: Any) -> None:
    """Signal handler to be connected to the 'pre_delete' signal for models that inherit from
    MediaParentMixin. It is responsible for removing child media that are associated with the
    object being deleted.
    """
    if kwargs.get("raw", False):
        return

    instance_ct = ContentType.objects.get_for_model(instance)
    for model_class in get_media_child_models():
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


def register_signal_handlers() -> None:
    """Register signal handlers for models using the private media system."""
    for model_class in get_media_parent_models():
        post_save.connect(
            assign_unparented_media_post_save,
            sender=model_class,
            dispatch_uid="assign_unparented_media",
        )
        post_delete.connect(
            update_child_media_on_delete,
            sender=model_class,
            dispatch_uid="update_custom_permission_policies",
        )
