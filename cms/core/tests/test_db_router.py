import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import router, transaction
from wagtail.models import Page

pytestmark = pytest.mark.django_db(transaction=True)


def test_uses_replica_for_read():
    """Check the read replica is used for reads, and the default for writes."""
    assert router.db_for_write(Page) == "default"
    assert router.db_for_read(Page) == "read_replica"


def test_uses_write_db_during_transaction():
    """Check the default is used for reads in a transaction."""
    assert router.db_for_read(Page) == "read_replica"

    with transaction.atomic():
        assert router.db_for_read(Page) == "default"

    assert router.db_for_read(Page) == "read_replica"


def test_uses_write_db_when_autocommit_disabled():
    """Check the default is used for reads when not in an autocommit context."""
    assert router.db_for_read(Page) == "read_replica"

    try:
        transaction.set_autocommit(False)
        assert router.db_for_read(Page) == "default"
    finally:
        transaction.set_autocommit(True)

    assert router.db_for_read(Page) == "read_replica"


def test_uses_correct_db_in_query():
    """Check the read replica is used when running an actual query."""
    # Choose a model which definitely exists
    content_type = ContentType.objects.first()

    assert content_type is not None
    assert content_type._state.db == "read_replica"  # pylint: disable=protected-access


def test_uses_correct_db_in_transaction():
    """Check the read replica is used when running a query inside a transaction."""
    # Choose a model which definitely exists
    with transaction.atomic():
        content_type = ContentType.objects.first()

    assert content_type is not None
    assert content_type._state.db == "default"  # pylint: disable=protected-access
