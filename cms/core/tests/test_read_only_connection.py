from django.db import DEFAULT_DB_ALIAS, connections, router
from django.db.utils import InternalError
from django.test import TestCase, override_settings
from django.utils.connection import ConnectionDoesNotExist
from wagtail_factories import ImageFactory

from cms.core.db_router import READ_REPLICA_DB_ALIAS, ExternalEnvRouter
from cms.core.tests import TransactionTestCase
from cms.images.models import CustomImage, Rendition
from cms.users.models import User
from cms.users.tests.factories import UserFactory


@override_settings(IS_EXTERNAL_ENV=True)
class ExternalReadOnlyConnectionTestCase(TestCase):
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
        self.assertEqual(router.db_for_read(CustomImage), DEFAULT_DB_ALIAS)  # TestCase runs in a transaction
        self.assertEqual(router.db_for_write(CustomImage), ExternalEnvRouter.FAKE_BACKEND)


class ReadOnlyConnectionTestCase(TransactionTestCase):
    def test_read_replica_connection_is_read_only(self):
        UserFactory.create()

        with self.assertRaisesMessage(InternalError, "cannot execute DELETE in a read-only transaction"):
            User.objects.all().using(READ_REPLICA_DB_ALIAS).delete()

    def test_raw_sql_is_read_only(self):
        with (
            self.assertRaisesMessage(InternalError, "cannot execute DELETE in a read-only transaction"),
            connections[READ_REPLICA_DB_ALIAS].cursor() as c,
        ):
            c.execute(f"DELETE FROM {User._meta.db_table} WHERE 1=1;")  # noqa: S608
