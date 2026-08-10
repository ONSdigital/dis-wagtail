"""Tests for audit logging infrastructure.

This module tests the signal handlers that mirror all Wagtail log entries to stdout
for protective monitoring and SIEM integration.
"""

from typing import Any
from unittest.mock import patch

from django.test import TestCase
from wagtail.log_actions import log
from wagtail.test.utils import WagtailTestUtils

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.tests.factories import BundleFactory


class AuditSignalHandlerTestCase(WagtailTestUtils, TestCase):
    """Test audit signal handlers for log entry mirroring."""

    def test_page_log_entry_mirrors_to_stdout(self) -> None:
        """Test that PageLogEntry creation triggers audit logging to stdout."""
        page = StatisticalArticlePageFactory()

        with patch("cms.core.audit.audit_logger") as mock_logger:
            log(action="wagtail.edit", instance=page)

            # Verify audit logger was called
            mock_logger.info.assert_called_once()
            call_args: tuple[tuple[Any, ...], dict[str, Any]] = mock_logger.info.call_args
            assert call_args[0][0] == "Audit event: %s"
            assert call_args[0][1] == "wagtail.edit"

            # Verify extra data
            extra: dict[str, Any] = call_args[1]["extra"]
            assert extra["event"] == "wagtail.edit"
            assert extra["object_type"] == "statistical article page"
            assert extra["object_id"] == page.id
            assert "object_label" in extra
            assert "timestamp" in extra

    def test_model_log_entry_mirrors_to_stdout(self) -> None:
        """Test that ModelLogEntry creation triggers audit logging to stdout."""
        bundle = BundleFactory()

        with patch("cms.core.audit.audit_logger") as mock_logger:
            log(action="wagtail.create", instance=bundle)

            # Verify audit logger was called
            mock_logger.info.assert_called_once()
            call_args: tuple[tuple[Any, ...], dict[str, Any]] = mock_logger.info.call_args
            assert call_args[0][0] == "Audit event: %s"
            assert call_args[0][1] == "wagtail.create"

            # Verify extra data
            extra: dict[str, Any] = call_args[1]["extra"]
            assert extra["event"] == "wagtail.create"
            assert extra["object_type"] == "bundle"
            assert extra["object_id"] == str(bundle.id)
            assert extra["object_label"] == str(bundle)
            assert "timestamp" in extra

    def test_log_entry_with_data_field(self) -> None:
        """Test that log entries with data field include it in stdout logging."""
        bundle = BundleFactory()

        with patch("cms.core.audit.audit_logger") as mock_logger:
            log(
                action="bundles.teams_changed",
                instance=bundle,
                data={"added_teams": ["Test Team"], "removed_teams": []},
            )

            # Verify data is included
            call_args: tuple[tuple[Any, ...], dict[str, Any]] = mock_logger.info.call_args
            extra: dict[str, Any] = call_args[1]["extra"]
            assert extra["data"] == {"added_teams": ["Test Team"], "removed_teams": []}

    def test_log_entry_without_user(self) -> None:
        """Test that log entries without a user don't crash."""
        bundle = BundleFactory()

        with patch("cms.core.audit.audit_logger") as mock_logger:
            # Log without a user to test system actions
            log(action="wagtail.create", instance=bundle, user=None)

            # Verify email is None when user is None
            call_args: tuple[tuple[Any, ...], dict[str, Any]] = mock_logger.info.call_args
            extra: dict[str, Any] = call_args[1]["extra"]
            assert extra["user_id"] is None
            assert extra["email"] is None

    def test_log_entry_update_not_logged(self) -> None:
        """Test that updates to existing log entries don't trigger audit logging."""
        bundle = BundleFactory()

        with patch("cms.core.audit.audit_logger") as mock_logger:
            # Create log entry
            entry = log(action="wagtail.create", instance=bundle)

            # Reset mock
            mock_logger.reset_mock()

            # Update the log entry (should not trigger audit logging)
            entry.save()

            # Verify audit logger was not called
            mock_logger.info.assert_not_called()
