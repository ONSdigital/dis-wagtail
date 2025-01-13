import json
from contextlib import ExitStack, contextmanager

from django.db import DEFAULT_DB_ALIAS, connections
from django.test import TransactionTestCase as _TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils.functional import partition

from cms.core.db_router import READ_REPLICA_DB_ALIAS


class TransactionTestCase(_TransactionTestCase):
    """A modified TransactionTestCase which ensures models created during migrations are accessible,
    and adds helpers for testing with multiple database connections.
    """

    databases = "__all__"

    # The site depends on instances created during migrations, so rollback must be serialized.
    serialized_rollback = True

    def _fixture_setup(self):
        """Set up fixtures for test cases."""
        if self.serialized_rollback and (
            fixtures := getattr(connections[DEFAULT_DB_ALIAS], "_test_serialized_contents", None)
        ):
            # Parse the fixture directly rather than serializing it into models for performance reasons.
            fixtures = json.loads(fixtures)

            # HACK: Wagtail's locales are read from a pre-save hook, which means they need to exist
            # very early when loading data.
            # TODO: Remove after https://github.com/wagtail/wagtail/pull/12649 merges.
            fixtures, eager_fixtures = partition(lambda item: item["model"] == "wagtailcore.locale", fixtures)

            connections[DEFAULT_DB_ALIAS]._test_serialized_contents = json.dumps(eager_fixtures + fixtures)  # pylint: disable=protected-access

        super()._fixture_setup()

    @contextmanager
    def assertTotalNumQueries(self, num):  # pylint: disable=invalid-name
        """Assert the total number of queries, regardless of the connection used."""
        with ExitStack() as context_stack:
            capture_query_contexts = [
                context_stack.enter_context(CaptureQueriesContext(conn)) for conn in connections.all()
            ]

            yield

        queries = sorted(
            query["sql"] for captured_query_context in capture_query_contexts for query in captured_query_context
        )

        self.assertEqual(
            len(queries),
            num,
            f"{len(queries)} queries executed, {num} expected\nCaptured queries were (in alphabetical order):\n"
            + "\n".join(queries),
        )

    @contextmanager
    def assertNumQueriesConnection(self, *, default=0, replica=0):  # pylint: disable=invalid-name
        """Assert the number of queries per connection."""
        with (
            self.assertNumQueries(default, using=DEFAULT_DB_ALIAS),
            self.assertNumQueries(replica, using=READ_REPLICA_DB_ALIAS),
        ):
            yield

    @contextmanager
    def captureQueries(self):  # pylint: disable=invalid-name
        """Capture the executed queries for the default and replica connections."""
        with (
            CaptureQueriesContext(connections[DEFAULT_DB_ALIAS]) as default_queries,
            CaptureQueriesContext(connections[READ_REPLICA_DB_ALIAS]) as replica_queries,
        ):
            yield default_queries, replica_queries
