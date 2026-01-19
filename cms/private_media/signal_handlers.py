from typing import TYPE_CHECKING, Any

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models import CharField, IntegerField
from django.db.models.functions import Cast
from wagtail.models import Page, ReferenceIndex
from wagtail.signals import published, unpublished

from cms.private_media.constants import Privacy
from cms.private_media.models import PrivateImageMixin
from cms.private_media.utils import get_private_media_models

if TYPE_CHECKING:
    from django.db.models import Model


def publish_media_on_publish(instance: Model, **kwargs: Any) -> None:
    """Signal handler to be connected to the 'page_published' and 'published'
    signals for all publishable models. It is responsible for identifying any
    privacy-controlled media used by the object, and ensuring that it is also
    made public.
    """
    for model_class in get_private_media_models():
        model_ct = ContentType.objects.get_for_model(model_class)
        referenced_pks = (
            ReferenceIndex.get_references_for_object(instance)
            .filter(to_content_type=model_ct)
            .annotate(int_object_id=Cast("to_object_id", output_field=IntegerField()))
            .values_list("int_object_id", flat=True)
            .distinct()
        )
        queryset = model_class.objects.filter(pk__in=referenced_pks, _privacy=Privacy.PRIVATE)
        if issubclass(model_class, PrivateImageMixin):
            queryset = queryset.prefetch_related("renditions")

        if hasattr(model_class.objects, "bulk_make_public"):
            model_class.objects.bulk_make_public(queryset)
        else:
            raise ImproperlyConfigured(
                f"The manager for {model_class.__name__} is missing a bulk_make_public() method implementation. "
                "Did you override the manager class and forget to subclass PrivateMediaModelManager?",
            )


def unpublish_media_on_unpublish(instance: Model, **kwargs: Any) -> None:
    """Signal handler to be connected to the 'page_unpublished' and 'unpublished'
    signals for all publishable models. It is responsible for identifying any
    privacy-controlled media used solely by the object, and ensuring that it is
    made private again.
    """
    page_ct = ContentType.objects.get_for_model(Page)
    for model_class in get_private_media_models():
        model_ct = ContentType.objects.get_for_model(model_class)
        references = ReferenceIndex.get_references_for_object(instance).filter(to_content_type=model_ct)
        referenced_pks = set(references.values_list("to_object_id", flat=True).distinct())
        if not referenced_pks:
            continue

        # Identify references from other pages and extract their IDs, so that we can
        # figure out which of those pages is live
        referencing_page_ids = (
            ReferenceIndex.objects.filter(to_content_type=model_ct, to_object_id__in=referenced_pks)
            .exclude(pk__in=references.values_list("pk", flat=True))
            .filter(base_content_type=page_ct)
            .annotate(page_id=Cast("object_id", output_field=IntegerField()))
            .values_list("page_id", flat=True)
            .distinct()
        )

        # Out of the pages that are referencing the media, identify the ids of those
        # that are currently live
        live_page_ids = (
            Page.objects.filter(pk__in=referencing_page_ids)
            .live()
            .annotate(str_id=Cast("id", output_field=CharField()))
            .values_list("str_id", flat=True)
        )

        # Now we can identify references from live pages only, and
        # generate a list of media item ids that should not be made private
        live_page_referenced_media_pks = (
            ReferenceIndex.objects.filter(to_content_type=model_ct, to_object_id__in=referenced_pks)
            .filter(base_content_type=page_ct, object_id__in=live_page_ids)
            .annotate(int_id=Cast("to_object_id", output_field=IntegerField()))
            .values_list("int_id", flat=True)
            .distinct()
        )

        queryset = (
            model_class.objects.all()
            .filter(pk__in=[int(pk) for pk in referenced_pks], _privacy=Privacy.PUBLIC)
            .exclude(pk__in=live_page_referenced_media_pks)
        )
        if issubclass(model_class, PrivateImageMixin):
            queryset = queryset.prefetch_related("renditions")

        if hasattr(model_class.objects, "bulk_make_private"):
            model_class.objects.bulk_make_private(queryset)
        else:
            raise ImproperlyConfigured(
                f"The manager for {model_class.__name__} is missing a bulk_make_private() method implementation. "
                "Did you override the manager class and forget to subclass PrivateMediaModelManager?",
            )


def register_signal_handlers() -> None:
    """Register signal handlers for models using the private media system."""
    published.connect(publish_media_on_publish, dispatch_uid="publish_media")
    unpublished.connect(unpublish_media_on_unpublish, dispatch_uid="unpublish_media")
