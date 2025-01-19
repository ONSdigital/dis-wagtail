import contextlib
from collections.abc import Sequence
from operator import itemgetter
from typing import TYPE_CHECKING

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.utils.text import capfirst

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from cms.datavis.models import Visualisation


def numberfy(value: str) -> int | float | str:
    stripped = value.strip()
    if stripped.isdigit():
        return int(stripped)
    with contextlib.suppress(ValueError):
        return float(stripped)
    return value


def get_child_model_from_name(parent_model: type["Model"], name: str) -> type["Model"]:
    model = apps.get_model(name)
    if not issubclass(model, parent_model):
        raise ValueError(f"'{name}' is not a subclass of {parent_model.__name__}")
    return model


def get_creatable_child_models(parent_model: type["Model"]) -> Sequence[type["Model"]]:
    return [
        model for model in apps.get_models() if issubclass(model, parent_model) and getattr(model, "is_creatable", True)
    ]


def get_creatable_child_model_choices(parent_model: type["Model"]) -> Sequence[tuple[str, str]]:
    choices = []
    for model in get_creatable_child_models(parent_model):
        choices.append((model._meta.label_lower, capfirst(str(model._meta.verbose_name))))
    return sorted(choices, key=itemgetter(1))


def get_creatable_visualisation_models() -> Sequence[type["Visualisation"]]:
    from cms.datavis.models import Visualisation  # pylint: disable=import-outside-toplevel

    return [model for model in apps.get_models() if issubclass(model, Visualisation) and model.is_creatable]


def get_creatable_visualisation_model_choices() -> Sequence[tuple[str, str]]:
    from cms.datavis.models import Visualisation  # pylint: disable=import-outside-toplevel

    return get_creatable_child_model_choices(Visualisation)


def get_creatable_visualisation_content_types() -> "QuerySet[ContentType]":
    """Returns a queryset of all ContentType objects corresponding to Visualisation model classes."""
    models = get_creatable_visualisation_models()

    content_type_ids = [ct.pk for ct in ContentType.objects.get_for_models(*models, for_concrete_models=False).values()]
    return ContentType.objects.filter(pk__in=content_type_ids).order_by("model")
