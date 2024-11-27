from wagtail.models import Page

from cms.core.tests import ReadOnlyConnectionTestCase

from .factories import ContactDetailsFactory


class ReadOnlyConnectionTestCaseTestCase(ReadOnlyConnectionTestCase):
    """A test case for connection assertions."""

    def test_assert_no_write_queries(self):
        """Test assertNoWriteQueries."""
        with self.assertNoWriteQueries():
            pass

        with self.assertNoWriteQueries():
            Page.objects.count()

        with self.assertRaises(AssertionError), self.assertNoWriteQueries():
            ContactDetailsFactory.create()

    def test_assert_no_default_queries(self):
        """Test assertNoDefaultQueries."""
        with self.assertNoDefaultQueries():
            Page.objects.using("read_replica").count()

        with self.assertRaises(AssertionError), self.assertNoDefaultQueries():
            Page.objects.using("default").count()
