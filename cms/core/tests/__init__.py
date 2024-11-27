from contextlib import contextmanager

from django.db import connections
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext


class ReadOnlyConnectionTestCase(TransactionTestCase):
    """A base test case for testing the read only connection.

    This test case must use TransactionTestCase rather than TestCase so the router
    chooses the correct connection.
    """

    databases = frozenset({"default", "read_replica"})

    READ_QUERY_PREFIXES = ("SELECT", "BEGIN", "COMMIT")

    @contextmanager
    def assertNoWriteQueries(self):  # pylint: disable=invalid-name
        """Assert that no write queries were performed in the given context.

        This intentionally checks all connections, rather than relying on the database router.
        """
        with (
            CaptureQueriesContext(connections["default"]) as captured_default_queries,
            CaptureQueriesContext(connections["read_replica"]) as captured_replica_queries,
        ):
            yield

        queries = [
            query["sql"]
            for query in (captured_default_queries.captured_queries + captured_replica_queries.captured_queries)
        ]

        write_queries = sorted(query for query in queries if not query.startswith(self.READ_QUERY_PREFIXES))

        self.assertEqual(len(write_queries), 0, "Write queries were executed:\n" + "\n".join(write_queries))

    @contextmanager
    def assertNoDefaultQueries(self):  # pylint: disable=invalid-name
        """Assert that no queries were performed against the "default" database in the given context."""
        with self.assertNumQueries(0, using="default"):
            yield
