import json
from contextlib import ExitStack, contextmanager

from django.db import connections
from django.test import TransactionTestCase as _TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils.functional import partition


class ConnectionHelperMixin:
    """A collection of helpers for testing the read replica handling."""

    databases = "__all__"

    READ_QUERY_PREFIXES = ("SELECT", "BEGIN", "COMMIT", "RELEASE", "SAVEPOINT")

    @contextmanager
    def assertNumWriteQueries(self, num):  # pylint: disable=invalid-name
        """Assert that no write queries were performed in the given context.

        This intentionally checks all connections, rather than relying on the database router.
        """
        with ExitStack() as context_stack:
            capture_query_contexts = [
                context_stack.enter_context(CaptureQueriesContext(conn)) for conn in connections.all()
            ]

            yield

        queries = [
            query["sql"] for captured_query_context in capture_query_contexts for query in captured_query_context
        ]

        write_queries = sorted(query for query in queries if not query.startswith(self.READ_QUERY_PREFIXES))

        self.assertEqual(
            len(write_queries),
            num,
            f"{len(write_queries)} write queries executed, {num} expected\nCaptured queries were:\n"
            + "\n".join(write_queries),
        )

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
            f"{len(queries)} queries executed, {num} expected\nCaptured queries were:\n" + "\n".join(queries),
        )

    @contextmanager
    def assertNoDefaultQueries(self):  # pylint: disable=invalid-name
        """Assert that no queries were performed against the "default" database in the given context."""
        with self.assertNumQueries(0, using="default"):
            yield

    @contextmanager
    def assertNumQueriesConnection(self, default, replica):
        with (
            self.assertNumQueries(default, using="default"),
            self.assertNumQueries(replica, using="read_replica"),
        ):
            yield


class TransactionTestCase(_TransactionTestCase, ConnectionHelperMixin):
    """A modified TransactionTestCase which ensures models created during migrations are accessible."""

    databases = "__all__"

    # The site depends on instances created during migrations, so rollback must be serialized.
    serialized_rollback = True

    def _fixture_setup(self):
        """Set up fixtures for test cases."""
        if self.serialized_rollback and not getattr(self, "_fixtures_rewritten", False) and (
            fixtures := getattr(connections["default"], "_test_serialized_contents", None)
        ):
            # Parse the fixture directly rather than serializing it into models for performance reasons.
            fixtures = json.loads(fixtures)

            # HACK: Wagtail's locales are read from a pre-save hook, which means they need to exist
            # very early during model setup.
            fixtures, eager_fixtures = partition(lambda item: item["model"] == "wagtailcore.locale", fixtures)

            connections["default"]._test_serialized_contents = json.dumps(eager_fixtures + fixtures)

            self._fixtures_rewritten = True

        super()._fixture_setup()
