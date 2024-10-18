"""Django creates redundant migrations for Django model changes that do not alter the database.

This patches the Django migration machinery to ignore various attrs.

The `makemigrations` and `migrate`  management commands will ignore the attrs defined in:

    - MIGRATION_IGNORE_MODEL_ATTRS
    - MIGRATION_IGNORE_FIELD_ATTRS
    - MIGRATION_IGNORE_FILE_FIELD_ATTRS
    - MIGRATION_IGNORE_RELATED_FIELD_ATTRS

This will reduce the amount of migrations and therefore speed-up development.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.db.migrations.operations import AlterModelOptions
from django.db.models import Field, FileField
from django.db.models.fields.related import RelatedField

logger = logging.getLogger(__name__)

MIGRATION_IGNORE_MODEL_ATTRS = ["verbose_name", "verbose_name_plural"]
MIGRATION_IGNORE_FIELD_ATTRS = ["validators", "choices", "help_text", "verbose_name"]
MIGRATION_IGNORE_FILE_FIELD_ATTRS = ["upload_to", "storage"]

MIGRATION_IGNORE_RELATED_FIELD_ATTRS = ["related_query_name"]

for attr in MIGRATION_IGNORE_MODEL_ATTRS:
    logger.debug(f"Model {attr} attr will be ignored.")

for attr in MIGRATION_IGNORE_FIELD_ATTRS:
    logger.debug(f"Field {attr} attr will be ignored.")

for attr in MIGRATION_IGNORE_FILE_FIELD_ATTRS:
    logger.debug(f"File field {attr} attr will be ignored.")

for attr in MIGRATION_IGNORE_RELATED_FIELD_ATTRS:
    logger.debug(f"Related field {attr} attr will be ignored.")


def patch_ignored_model_attrs(cls: type[AlterModelOptions]) -> None:
    for attribute in MIGRATION_IGNORE_MODEL_ATTRS:
        if attribute in cls.ALTER_OPTION_KEYS:
            cls.ALTER_OPTION_KEYS.remove(attribute)


def patch_field_deconstruct(old_func: Callable) -> Callable:
    @wraps(old_func)
    def deconstruct_with_ignored_attrs(self: Field) -> tuple[str, str, Any, Any]:
        name, path, args, kwargs = old_func(self)
        for attribute in MIGRATION_IGNORE_FIELD_ATTRS:
            kwargs.pop(attribute, None)
        return name, path, args, kwargs

    return deconstruct_with_ignored_attrs


def patch_file_field_deconstruct(old_func: Callable) -> Callable:
    @wraps(old_func)
    def deconstruct_with_ignored_attrs(self: FileField) -> tuple[str, str, Any, Any]:
        name, path, args, kwargs = old_func(self)
        for attribute in MIGRATION_IGNORE_FILE_FIELD_ATTRS:
            kwargs.pop(attribute, None)
        return name, path, args, kwargs

    return deconstruct_with_ignored_attrs


def patch_related_field_deconstruct(old_func: Callable) -> Callable:
    @wraps(old_func)
    def deconstruct_with_ignored_attrs(self: RelatedField) -> tuple[str, str, Any, Any]:
        name, path, args, kwargs = old_func(self)
        for attribute in MIGRATION_IGNORE_RELATED_FIELD_ATTRS:
            kwargs.pop(attribute, None)
        return name, path, args, kwargs

    return deconstruct_with_ignored_attrs


Field.deconstruct = patch_field_deconstruct(Field.deconstruct)  # type: ignore
FileField.deconstruct = patch_file_field_deconstruct(FileField.deconstruct)  # type: ignore
RelatedField.deconstruct = patch_related_field_deconstruct(RelatedField.deconstruct)  # type: ignore
patch_ignored_model_attrs(AlterModelOptions)
