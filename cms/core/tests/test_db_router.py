from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS, router, transaction
from wagtail.models import Page

from cms.core.db_router import READ_REPLICA_DB_ALIAS
from cms.core.tests import TransactionTestCase
from cms.home.models import HomePage
from cms.users.models import User


class DBRouterTestCase(TransactionTestCase):
    available_apps = frozenset({"cms.users"})

    def setUp(self):
        # Warm the content-type cache
        ContentType.objects.get_for_models(HomePage)

    def test_uses_replica_for_read(self):
        """Check the read replica is used for reads."""
        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)

    def test_uses_default_for_write(self):
        """Check the read replica is used for writes."""
        instance = Page.objects.first()

        self.assertIsNotNone(instance)

        self.assertEqual(router.db_for_write(Page), DEFAULT_DB_ALIAS)
        self.assertEqual(router.db_for_write(Page, instance=instance), DEFAULT_DB_ALIAS)

    def test_uses_write_db_for_read_during_transaction(self):
        """Check the default is used for reads in a transaction."""
        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)

        with transaction.atomic():
            self.assertEqual(router.db_for_read(Page), DEFAULT_DB_ALIAS)

        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)

    def test_uses_write_db_for_read_when_autocommit_disabled(self):
        """Check the default is used for reads when not in an autocommit context."""
        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)

        try:
            transaction.set_autocommit(False)
            self.assertEqual(router.db_for_read(Page), DEFAULT_DB_ALIAS)
        finally:
            transaction.set_autocommit(True)

        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)

    def test_uses_replica_db_in_query(self):
        """Check the read replica is used when running an actual query."""
        # Choose a model which definitely exists
        content_type = ContentType.objects.first()

        self.assertIsNotNone(content_type)
        self.assertEqual(content_type._state.db, READ_REPLICA_DB_ALIAS)  # pylint: disable=protected-access

    def test_uses_write_db_in_transaction(self):
        """Check the read replica is used when running a query inside a transaction."""
        # Choose a model which definitely exists
        with transaction.atomic():
            content_type = ContentType.objects.first()

        self.assertIsNotNone(content_type)
        self.assertEqual(content_type._state.db, DEFAULT_DB_ALIAS)  # pylint: disable=protected-access

    def test_search_uses_correct_db(self):
        """Check the read replica is used for search queries."""
        with self.assertNumQueriesConnection(replica=1):
            list(HomePage.objects.search("Home"))

    def test_deletes_from_default_when_read_from_replica(self):
        user = User.objects.create_user("user", "email@example.com", "password")

        self.assertEqual(user._state.db, DEFAULT_DB_ALIAS)  # pylint: disable=protected-access

        # HACK: The replica connection can't see the user right now for some reason
        user._state.db = READ_REPLICA_DB_ALIAS  # pylint: disable=protected-access

        self.assertEqual(router.db_for_write(User, instance=user), DEFAULT_DB_ALIAS)

        with self.captureQueries() as (default_queries, replica_queries), transaction.atomic():
            user.delete()

        default_delete_queries = [q for q in default_queries.captured_queries if q["sql"].startswith("DELETE")]
        replica_delete_queries = [q for q in replica_queries.captured_queries if q["sql"].startswith("DELETE")]

        self.assertGreater(len(default_delete_queries), 1)
        self.assertEqual(len(replica_delete_queries), 0)

        self.assertFalse(User.objects.using(DEFAULT_DB_ALIAS).filter(id=user.id).exists())
        self.assertFalse(User.objects.using(READ_REPLICA_DB_ALIAS).filter(id=user.id).exists())
