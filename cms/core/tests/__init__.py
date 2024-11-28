import json
from contextlib import ExitStack, contextmanager

from django.db import connections
from django.test import TransactionTestCase as _TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils.functional import partition


class TransactionTestCase(_TransactionTestCase):
    """A modified TransactionTestCase which ensures models created during migrations are accessible,
    and adds helpers for testing with multiple database connections.
    """

    databases = "__all__"

    # The site depends on instances created during migrations, so rollback must be serialized.
    serialized_rollback = True

    def _fixture_setup(self):
        """Set up fixtures for test cases."""
        if (
            self.serialized_rollback
            and not getattr(self, "_fixtures_rewritten", False)
            and (fixtures := getattr(connections["default"], "_test_serialized_contents", None))
        ):
            # Parse the fixture directly rather than serializing it into models for performance reasons.
            fixtures = json.loads(fixtures)

            # HACK: Wagtail's locales are read from a pre-save hook, which means they need to exist
            # very early during model setup.
            fixtures, eager_fixtures = partition(lambda item: item["model"] == "wagtailcore.locale", fixtures)

            connections["default"]._test_serialized_contents = json.dumps(eager_fixtures + fixtures)

            self._fixtures_rewritten = True

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
    def assertNumQueriesConnection(self, *, default=0, replica=0):
        with (
            self.assertNumQueries(default, using="default"),
            self.assertNumQueries(replica, using="read_replica"),
        ):
            yield
