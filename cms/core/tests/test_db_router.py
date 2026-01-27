from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS, router, transaction
from django.db.models.signals import post_save
from django.test import TestCase, override_settings
from django.utils.connection import ConnectionDoesNotExist
from modelsearch.signal_handlers import post_save_signal_handler
from wagtail.models import Page, Revision
from wagtail_factories import ImageFactory

from cms.core.db_router import READ_REPLICA_DB_ALIAS, ExternalEnvRouter, force_write_db, force_write_db_for_queryset
from cms.core.tests import TransactionTestCase
from cms.home.models import HomePage
from cms.images.models import CustomImage, Rendition
from cms.taxonomy.models import Topic
from cms.users.models import User


class DBRouterTestCase(TransactionTestCase):
    available_apps = frozenset({"cms.users"})

    @classmethod
    def setUpClass(cls):
        # Temporarily disconnecting the search post save signal handler for Topics to prevent noise in tests
        post_save.disconnect(post_save_signal_handler, sender=Topic)

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        post_save.connect(post_save_signal_handler, sender=Topic)

    def setUp(self):
        # Warm the content-type cache
        ContentType.objects.get_for_models(HomePage)
        ContentType.objects.get_for_models(Page)

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

    def test_uses_write_db_in_nested_transaction(self):
        """Check the default is used for reads in a nested transaction."""
        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)

        with transaction.atomic():
            self.assertEqual(router.db_for_read(Page), DEFAULT_DB_ALIAS)

            with transaction.atomic():
                self.assertEqual(router.db_for_read(Page), DEFAULT_DB_ALIAS)

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

    def test_revision_uses_default(self):
        """Checks that revisions (a model used in a GenericRelation)
        always uses the default connection.
        """
        self.assertEqual(router.db_for_write(Revision), DEFAULT_DB_ALIAS)
        self.assertEqual(router.db_for_read(Revision), DEFAULT_DB_ALIAS)

        # In the external env, no writes will be done, so the replica is safe.
        with override_settings(IS_EXTERNAL_ENV=True):
            self.assertEqual(router.db_for_read(Revision), READ_REPLICA_DB_ALIAS)

    def test_force_write_db_for_queryset(self):
        """Check that the force_write_db util works as expected."""
        qs = User.objects.all()

        self.assertEqual(qs.db, READ_REPLICA_DB_ALIAS)
        self.assertEqual(force_write_db_for_queryset(qs).db, DEFAULT_DB_ALIAS)

        with self.assertNumQueriesConnection():
            # Calling the method doesn't perform any queries
            force_write_db_for_queryset(qs)

        with self.assertNumQueriesConnection(default=1):
            list(force_write_db_for_queryset(qs))

    def test_force_write_db(self):
        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)

        with force_write_db():
            self.assertEqual(router.db_for_read(Page), DEFAULT_DB_ALIAS)

            with force_write_db():
                self.assertEqual(router.db_for_read(Page), DEFAULT_DB_ALIAS)

            self.assertEqual(router.db_for_read(Page), DEFAULT_DB_ALIAS)

        self.assertEqual(router.db_for_read(Page), READ_REPLICA_DB_ALIAS)


@override_settings(IS_EXTERNAL_ENV=True)
class ExternalEnvRouterTestCase(TestCase):
    def test_cannot_write_to_disallowed_table(self):
        """Test that disallowed models cannot be written to in external env."""
        self.assertFalse(CustomImage.objects.exists())

        with self.assertRaises(ConnectionDoesNotExist):
            ImageFactory.create()

        self.assertFalse(CustomImage.objects.exists())

    def test_can_write_to_allowed_table(self):
        """Test that allowed models can be written to in external env."""
        self.assertEqual(Rendition.objects.count(), 0)

        with override_settings(IS_EXTERNAL_ENV=False):
            image = ImageFactory.create()

        rendition = image.get_rendition("width-100")

        # Confirm instance exists in DB
        rendition.refresh_from_db()

        self.assertEqual(Rendition.objects.count(), 1)

    def test_uses_correct_connection(self):
        """Test that the correct connection is used."""
        self.assertEqual(router.db_for_read(Rendition), DEFAULT_DB_ALIAS)  # TestCase runs in a transaction

        for model in apps.get_models():
            with self.subTest(model=model):
                if model in ExternalEnvRouter.WRITE_ALLOWED_MODELS:
                    self.assertEqual(router.db_for_write(model), DEFAULT_DB_ALIAS)
                else:
                    self.assertEqual(router.db_for_write(model), ExternalEnvRouter.FAKE_BACKEND)
