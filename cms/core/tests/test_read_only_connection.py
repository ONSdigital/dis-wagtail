from django.db import connections
from django.db.models.signals import post_save
from django.db.utils import InternalError
from modelsearch.signal_handlers import post_save_signal_handler

from cms.core.db_router import READ_REPLICA_DB_ALIAS
from cms.core.tests import TransactionTestCase
from cms.taxonomy.models import Topic
from cms.users.models import User
from cms.users.tests.factories import UserFactory


class ReadOnlyConnectionTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # Temporarily disconnecting the search post save signal handler for Topics to prevent noise in tests
        post_save.disconnect(post_save_signal_handler, sender=Topic)

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        post_save.connect(post_save_signal_handler, sender=Topic)

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
