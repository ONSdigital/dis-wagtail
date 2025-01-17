from operator import itemgetter
from typing import TYPE_CHECKING

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.text import capfirst

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from cms.datavis.models import Visualisation


def get_creatable_visualisation_models() -> list[type["Visualisation"]]:
    from cms.datavis.models import Visualisation  # pylint: disable=import-outside-toplevel

    return [model for model in apps.get_models() if issubclass(model, Visualisation) and model.is_creatable]


def get_visualisation_type_model_from_name(name: str) -> type["Visualisation"]:
    from cms.datavis.models import Visualisation  # pylint: disable=import-outside-toplevel

    model = apps.get_model(name)
    if not issubclass(model, Visualisation):
        raise ValueError(f"'{name}' is not a subclass of Visualisation")
    return model


def get_visualisation_type_choices() -> list[tuple[str, str]]:
    choices = []
    for model in get_creatable_visualisation_models():
        choices.append((model._meta.label_lower, capfirst(model._meta.verbose_name)))
    return sorted(choices, key=itemgetter(1))


def get_visualisation_content_types() -> "QuerySet[ContentType]":
    """Returns a queryset of all ContentType objects corresponding to Visualisation model classes."""
    models = get_creatable_visualisation_models()

    content_type_ids = [ct.pk for ct in ContentType.objects.get_for_models(*models, for_concrete_models=False).values()]
    return ContentType.objects.filter(pk__in=content_type_ids).order_by("model")
