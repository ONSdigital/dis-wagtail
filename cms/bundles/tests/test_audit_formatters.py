"""Tests for bundle audit log formatters."""

from django.test import TestCase
from django.utils.html import escape
from wagtail.log_actions import log

from cms.bundles.tests.factories import BundleFactory
from cms.bundles.wagtail_hooks import format_added_removed_items


class FormatAddedRemovedItemsTestCase(TestCase):
    """Test the format_added_removed_items helper function."""

    def test_both_added_and_removed(self) -> None:
        """Test formatting when both items are added and removed."""
        result = format_added_removed_items(
            added_items=["Team A", "Team B"],
            removed_items=["Team C"],
        )

        # Check that both sections are present
        self.assertIn("Added:", str(result))
        self.assertIn("Removed:", str(result))
        self.assertIn("<strong>Team A</strong>", str(result))
        self.assertIn("<strong>Team B</strong>", str(result))
        self.assertIn("<strong>Team C</strong>", str(result))
        self.assertIn("<br>", str(result))

    def test_only_added_items(self) -> None:
        """Test formatting when only items are added."""
        result = format_added_removed_items(
            added_items=["Team A", "Team B"],
            removed_items=[],
        )

        # Check that only Added section is present
        self.assertIn("Added:", str(result))
        self.assertNotIn("Removed:", str(result))
        self.assertIn("<strong>Team A</strong>", str(result))
        self.assertIn("<strong>Team B</strong>", str(result))
        self.assertNotIn("<br>", str(result))

    def test_only_removed_items(self) -> None:
        """Test formatting when only items are removed."""
        result = format_added_removed_items(
            added_items=[],
            removed_items=["Team C", "Team D"],
        )

        # Check that only Removed section is present
        self.assertNotIn("Added:", str(result))
        self.assertIn("Removed:", str(result))
        self.assertIn("<strong>Team C</strong>", str(result))
        self.assertIn("<strong>Team D</strong>", str(result))
        self.assertNotIn("<br>", str(result))

    def test_empty_lists(self) -> None:
        """Test formatting when both lists are empty."""
        result = format_added_removed_items(
            added_items=[],
            removed_items=[],
        )

        # Should return empty result
        self.assertEqual(str(result), "")

    def test_with_context(self) -> None:
        """Test formatting with context text."""
        result = format_added_removed_items(
            added_items=["Team A"],
            removed_items=["Team B"],
            context="Changed preview teams in bundle",
        )

        # Check that context is present at the start
        self.assertIn("Changed preview teams in bundle", str(result))
        self.assertIn("Added:", str(result))
        self.assertIn("Removed:", str(result))
        # Context should come before Added/Removed
        self.assertTrue(str(result).index("Changed preview teams in bundle") < str(result).index("Added:"))

    def test_with_context_only_added(self) -> None:
        """Test formatting with context text when only items are added."""
        result = format_added_removed_items(
            added_items=["Team A"],
            removed_items=[],
            context="Changed preview teams in bundle",
        )

        # Check formatting
        self.assertIn("Changed preview teams in bundle", str(result))
        self.assertIn("Added:", str(result))
        self.assertNotIn("Removed:", str(result))

    def test_special_characters_escaped(self) -> None:
        """Test that special characters in item names are properly escaped."""
        result = format_added_removed_items(
            added_items=["Team <script>alert('xss')</script>"],
            removed_items=["Team & Co"],
        )

        # Check that HTML is escaped
        self.assertIn(escape("<script>alert('xss')</script>"), str(result))
        self.assertIn("&amp;", str(result))
        self.assertNotIn("<script>", str(result))


class BundleTeamsChangedFormatterTestCase(TestCase):
    """Test the bundles.teams_changed log formatter."""

    def test_teams_changed_formatter_both_added_and_removed(self) -> None:
        """Test formatter with both added and removed teams."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.teams_changed",
            instance=bundle,
            data={
                "added_teams": ["Team A", "Team B"],
                "removed_teams": ["Team C"],
            },
        )

        message = entry.formatter.format_message(entry)

        self.assertIn("Changed preview teams for bundle", str(message))
        self.assertIn("Added:", str(message))
        self.assertIn("<strong>Team A</strong>", str(message))
        self.assertIn("<strong>Team B</strong>", str(message))
        self.assertIn("Removed:", str(message))
        self.assertIn("<strong>Team C</strong>", str(message))

    def test_teams_changed_formatter_only_added(self) -> None:
        """Test formatter with only added teams."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.teams_changed",
            instance=bundle,
            data={
                "added_teams": ["Team A"],
                "removed_teams": [],
            },
        )

        message = entry.formatter.format_message(entry)

        self.assertIn("Changed preview teams for bundle", str(message))
        self.assertIn("Added:", str(message))
        self.assertIn("<strong>Team A</strong>", str(message))
        self.assertNotIn("Removed:", str(message))

    def test_teams_changed_formatter_only_removed(self) -> None:
        """Test formatter with only removed teams."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.teams_changed",
            instance=bundle,
            data={
                "added_teams": [],
                "removed_teams": ["Team C"],
            },
        )

        message = entry.formatter.format_message(entry)

        self.assertIn("Changed preview teams for bundle", str(message))
        self.assertNotIn("Added:", str(message))
        self.assertIn("Removed:", str(message))
        self.assertIn("<strong>Team C</strong>", str(message))

    def test_teams_changed_formatter_fallback(self) -> None:
        """Test formatter fallback when data is missing or empty."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.teams_changed",
            instance=bundle,
            data={},
        )

        message = entry.formatter.format_message(entry)

        # When data is empty/missing, formatter returns the context
        self.assertEqual(message, "Changed preview teams for bundle")


class BundlePagesChangedFormatterTestCase(TestCase):
    """Test the bundles.pages_changed log formatter."""

    def test_pages_changed_formatter_both_added_and_removed(self) -> None:
        """Test formatter with both added and removed pages."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.pages_changed",
            instance=bundle,
            data={
                "added_pages": ["Page 1", "Page 2"],
                "removed_pages": ["Page 3"],
            },
        )

        message = entry.formatter.format_message(entry)

        self.assertIn("Changed pages in bundle", str(message))
        self.assertIn("Added:", str(message))
        self.assertIn("<strong>Page 1</strong>", str(message))
        self.assertIn("<strong>Page 2</strong>", str(message))
        self.assertIn("Removed:", str(message))
        self.assertIn("<strong>Page 3</strong>", str(message))

    def test_pages_changed_formatter_only_added(self) -> None:
        """Test formatter with only added pages."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.pages_changed",
            instance=bundle,
            data={
                "added_pages": ["Page 1"],
                "removed_pages": [],
            },
        )

        message = entry.formatter.format_message(entry)

        self.assertIn("Changed pages in bundle", str(message))
        self.assertIn("Added:", str(message))
        self.assertIn("<strong>Page 1</strong>", str(message))
        self.assertNotIn("Removed:", str(message))

    def test_pages_changed_formatter_only_removed(self) -> None:
        """Test formatter with only removed pages."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.pages_changed",
            instance=bundle,
            data={
                "added_pages": [],
                "removed_pages": ["Page 3"],
            },
        )

        message = entry.formatter.format_message(entry)

        self.assertIn("Changed pages in bundle", str(message))
        self.assertNotIn("Added:", str(message))
        self.assertIn("Removed:", str(message))
        self.assertIn("<strong>Page 3</strong>", str(message))

    def test_pages_changed_formatter_fallback(self) -> None:
        """Test formatter fallback when data is missing."""
        bundle = BundleFactory()
        entry = log(
            action="bundles.pages_changed",
            instance=bundle,
            data={},
        )

        message = entry.formatter.format_message(entry)

        self.assertEqual(message, "Changed pages in bundle")
