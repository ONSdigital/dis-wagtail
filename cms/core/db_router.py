from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from asgiref.local import Local
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.models import Manager, Model, QuerySet

from cms.images.models import Rendition

READ_REPLICA_DB_ALIAS = "read_replica"

_force_write_db_for_context = Local()


def force_write_db_for[T: Model](queryset: QuerySet[T] | Manager[T]) -> QuerySet[T]:
    """Force the given queryset or manager to use the write DB, even for read queries.

    This is a helper function to make the intent clearer.
    """
    return queryset.using(DEFAULT_DB_ALIAS)


@contextmanager
def force_write_db() -> Generator[None]:
    """Force a given context to use the write DB, even for read queries.

    Note that this only applies to queries executed within the context, rather than
    querysets created there.
    """
    previous_value = getattr(_force_write_db_for_context, "value", None)

    try:
        _force_write_db_for_context.value = True
        yield
    finally:
        if previous_value is None:
            del _force_write_db_for_context.value
        else:
            _force_write_db_for_context.value = previous_value


class ReadReplicaRouter:  # pylint: disable=unused-argument,protected-access
    """A database router for directing queries between the default database and a read replica.

    This router routes read queries to a read replica while ensuring write queries
    (and migrations) are directed to the default database.

    https://docs.djangoproject.com/en/5.1/topics/db/multi-db/#automatic-database-routing
    """

    REPLICA_DBS = frozenset({READ_REPLICA_DB_ALIAS, DEFAULT_DB_ALIAS})

    def __init__(self) -> None:
        if READ_REPLICA_DB_ALIAS not in settings.DATABASES:  # pragma: no cover
            raise ImproperlyConfigured("Read replica is not configured.")

        # Collect models used in a GenericRelation to work around Django bug
        # @see db_for_read
        self.generic_target_models: set[type[Model]] = set()
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if isinstance(field, GenericRelation) and field.related_model != "self":
                    self.generic_target_models.add(field.related_model)

    def db_for_read(self, model: type[Model], **hints: Any) -> str | None:
        """Determine which database should be used for read queries."""
        if getattr(_force_write_db_for_context, "value", False):
            return DEFAULT_DB_ALIAS

        # Models used in a GenericRelation must use the write connection.
        # @see https://code.djangoproject.com/ticket/36389
        if not settings.IS_EXTERNAL_ENV and model in self.generic_target_models:
            return DEFAULT_DB_ALIAS

        # If the write database is in a (uncommitted) transaction,
        # a subsequent SELECT (or other read query) may return inconsistent data.
        # In this case, use the write connection for reads, with the aim of
        # improved consistency.
        if not transaction.get_autocommit(using=DEFAULT_DB_ALIAS):
            # In a transaction, use the write database
            return DEFAULT_DB_ALIAS

        return READ_REPLICA_DB_ALIAS

    def db_for_write(self, model: type[Model], **hints: Any) -> str | None:
        """Determine which database should be used for write queries."""
        # The default MUST be used
        return DEFAULT_DB_ALIAS

    def allow_relation(self, obj1: Model, obj2: Model, **hints: Any) -> bool | None:
        """Determine whether a relation is allowed between two models."""
        # If both instances are in the same database (or its replica), allow relations
        if obj1._state.db in self.REPLICA_DBS and obj2._state.db in self.REPLICA_DBS:
            return True

        # No preference
        return None

    def allow_migrate(self, db: str, app_label: str, model_name: str | None = None, **hints: Any) -> bool | None:
        """Determine whether migrations be run for the app on the database."""
        # Don't allow migrations to run against the replica (they would fail anyway)
        if db == READ_REPLICA_DB_ALIAS:
            return False

        # No preference
        return None


class ExternalEnvRouter:  # pylint: disable=unused-argument,protected-access
    """A database router which prevents writes to certain models in the external environment.

    In production, this will also be enforced at the database level.
    """

    WRITE_ALLOWED_MODELS = frozenset({Rendition})

    FAKE_BACKEND = "not_allowed_in_external_env"

    def db_for_write(self, model: type[Model], **hints: Any) -> str | None:
        """Determine which database should be used for write queries."""
        if settings.IS_EXTERNAL_ENV and model not in self.WRITE_ALLOWED_MODELS:
            # Return a fake (non-existent) backend so Django can still resolve the backend, it just can't
            # connect to it.
            return self.FAKE_BACKEND

        # No preference
        return None

    def allow_relation(self, obj1: Model, obj2: Model, **hints: Any) -> bool | None:
        """Determine whether a relation is allowed between two models."""
        # If any models have a fake backend, assume they can be related to placate Django.
        if self.FAKE_BACKEND in [obj1._state.db, obj2._state.db]:
            return True

        # No preference
        return None

    def allow_migrate(self, db: str, app_label: str, model_name: str | None = None, **hints: Any) -> bool | None:
        """Determine whether migrations be run for the app on the database."""
        # Don't allow migrations to run against the fake database (they would fail anyway)
        if db == self.FAKE_BACKEND:
            return False

        # No preference
        return None
