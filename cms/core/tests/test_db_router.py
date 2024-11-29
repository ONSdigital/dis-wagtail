from django.contrib.contenttypes.models import ContentType
from django.db import router, transaction
from django.test import TransactionTestCase
from wagtail.models import Page

from cms.home.models import HomePage


class DBRouterTestCase(TransactionTestCase):
    databases = frozenset({"default", "read_replica"})

    def test_uses_replica_for_read(self):
        """Check the read replica is used for reads, and the default for writes."""
        self.assertEqual(router.db_for_write(Page), "default")
        self.assertEqual(router.db_for_read(Page), "read_replica")

    def test_uses_write_db_during_transaction(self):
        """Check the default is used for reads in a transaction."""
        self.assertEqual(router.db_for_read(Page), "read_replica")

        with transaction.atomic():
            self.assertEqual(router.db_for_read(Page), "default")

        self.assertEqual(router.db_for_read(Page), "read_replica")

    def test_uses_write_db_when_autocommit_disabled(self):
        """Check the default is used for reads when not in an autocommit context."""
        self.assertEqual(router.db_for_read(Page), "read_replica")

        try:
            transaction.set_autocommit(False)
            self.assertEqual(router.db_for_read(Page), "default")
        finally:
            transaction.set_autocommit(True)

        self.assertEqual(router.db_for_read(Page), "read_replica")

    def test_uses_correct_db_in_query(self):
        """Check the read replica is used when running an actual query."""
        # Choose a model which definitely exists
        content_type = ContentType.objects.first()

        self.assertIsNotNone(content_type)
        self.assertEqual(content_type._state.db, "read_replica")  # pylint: disable=protected-access

    def test_uses_correct_db_in_transaction(self):
        """Check the read replica is used when running a query inside a transaction."""
        # Choose a model which definitely exists
        with transaction.atomic():
            content_type = ContentType.objects.first()

        self.assertIsNotNone(content_type)
        self.assertEqual(content_type._state.db, "default")  # pylint: disable=protected-access

    def test_search_uses_correct_db(self):
        """Check the read replica is used for search queries."""
        with self.assertNumQueries(2, using="read_replica"), self.assertNumQueries(0, using="default"):
            list(HomePage.objects.search("Home"))
