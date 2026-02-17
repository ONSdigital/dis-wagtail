from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import Mock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from slack_sdk.errors import SlackApiError

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.notifications.api_failures import (
    notify_slack_of_dataset_api_failure,
    notify_slack_of_third_party_api_failure,
)
from cms.bundles.notifications.slack import (
    _format_publish_datetime,
    _get_bundle_notification_context,
    _get_example_page_url,
    _get_publish_type,
    _send_and_update_message,
    get_slack_client,
    notify_slack_of_bundle_failure,
    notify_slack_of_bundle_pre_publish,
    notify_slack_of_publication_start,
    notify_slack_of_publish_end,
    notify_slack_of_status_change,
)
from cms.bundles.tests.factories import BundleFactory
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from cms.users.tests.factories import UserFactory


class GetSlackClientTestCase(TestCase):
    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token")
    @patch("cms.bundles.notifications.slack.WebClient")
    def test_get_slack_client__with_token(self, mock_client):
        """Should return WebClient instance when token is configured."""
        client = get_slack_client()
        self.assertIsNotNone(client)
        mock_client.assert_called_once_with(token="xoxb-test-token")

    @override_settings(SLACK_BOT_TOKEN=None)
    def test_get_slack_client__without_token(self):
        """Should return None when token is not configured."""
        client = get_slack_client()
        self.assertIsNone(client)


class SendAndUpdateMessageTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Test Bundle", bundled_pages=[StatisticalArticlePageFactory()])

    def setUp(self):
        self.mock_response = {"ok": True, "ts": "1503435956.000247", "channel": "C024BE91L"}

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_send_and_update_message__create_new_message(self, mock_get_client):
        """Should create a new message when bundle has no stored timestamp."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = self.mock_response
        mock_get_client.return_value = mock_client

        fields = [{"title": "Test", "value": "Value", "short": True}]
        _send_and_update_message(
            bundle=self.bundle,
            text="Test message",
            color="good",
            fields=fields,
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]
        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["text"], "Test message")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "good")
        self.assertEqual(call_kwargs["attachments"][0]["fields"], fields)
        self.assertFalse(call_kwargs["unfurl_links"])
        self.assertFalse(call_kwargs["unfurl_media"])

        # Verify timestamp was stored
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.slack_notification_ts, "1503435956.000247")

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_send_and_update_message__update_existing_message(self, mock_get_client):
        """Should update existing message when bundle has stored timestamp."""
        self.bundle.slack_notification_ts = "1503435956.000247"
        self.bundle.save()

        mock_client = Mock()
        mock_client.chat_update.return_value = self.mock_response
        mock_get_client.return_value = mock_client

        fields = [{"title": "Test", "value": "Updated Value", "short": True}]
        _send_and_update_message(
            bundle=self.bundle,
            text="Updated message",
            color="warning",
            fields=fields,
        )

        mock_client.chat_update.assert_called_once()
        call_kwargs = mock_client.chat_update.call_args[1]
        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["ts"], "1503435956.000247")
        self.assertEqual(call_kwargs["text"], "Updated message")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "warning")

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_send_and_update_message__fallback_on_update_failure(self, mock_get_client):
        """Should create new message if update fails."""
        self.bundle.slack_notification_ts = "1503435956.000247"
        self.bundle.save()

        mock_client = Mock()
        mock_client.chat_update.side_effect = SlackApiError(
            "message not found", response={"error": "message_not_found"}
        )
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1503435957.000248", "channel": "C024BE91L"}
        mock_get_client.return_value = mock_client

        fields = [{"title": "Test", "value": "Value", "short": True}]
        _send_and_update_message(
            bundle=self.bundle,
            text="Test message",
            color="good",
            fields=fields,
        )

        # Should have called update first, then fallback to postMessage
        mock_client.chat_update.assert_called_once()
        mock_client.chat_postMessage.assert_called_once()

        # Verify new timestamp was stored
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.slack_notification_ts, "1503435957.000248")

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_send_and_update_message__no_channel_configured(self, mock_get_client):
        """Should return early with warning if no channel is configured."""
        with self.assertLogs("cms.bundles", level="WARNING") as logs:
            _send_and_update_message(
                bundle=self.bundle,
                text="Test message",
                color="good",
                fields=[],
            )
            self.assertIn("SLACK_NOTIFICATION_CHANNEL not configured", logs.output[0])
            mock_get_client.assert_not_called()

    @override_settings(SLACK_BOT_TOKEN=None, SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_send_and_update_message__no_client(self, mock_get_client):
        """Should return early with warning if client is not configured."""
        mock_get_client.return_value = None

        with self.assertLogs("cms.bundles", level="WARNING") as logs:
            _send_and_update_message(
                bundle=self.bundle,
                text="Test message",
                color="good",
                fields=[],
            )
            self.assertIn("Slack Bot API client not configured", logs.output[0])


class SlackNotificationsBotAPITestCase(TestCase):
    """Tests for Bot API notifications."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="First Bundle", bundled_pages=[StatisticalArticlePageFactory()])
        cls.user = UserFactory(first_name="Publishing", last_name="Officer")
        request = RequestFactory().get("/")
        cls.inspect_url = request.build_absolute_uri(reverse("bundle:inspect", args=(cls.bundle.pk,)))

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_status_change__bot_api(self, mock_send):
        """Should use Bot API when fully configured."""
        self.bundle.status = BundleStatus.IN_REVIEW
        notify_slack_of_status_change(self.bundle, BundleStatus.DRAFT.label, self.user, self.inspect_url)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        self.assertEqual(call_kwargs["bundle"], self.bundle)
        self.assertEqual(call_kwargs["text"], "Bundle status changed")
        self.assertEqual(call_kwargs["color"], "good")
        self.assertIn({"title": "Title", "value": "First Bundle", "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "Changed by", "value": "Publishing Officer", "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "Old status", "value": BundleStatus.DRAFT.label, "short": True}, call_kwargs["fields"])
        self.assertIn(
            {"title": "New status", "value": BundleStatus.IN_REVIEW.label, "short": True}, call_kwargs["fields"]
        )
        self.assertIn({"title": "Link", "value": self.inspect_url, "short": False}, call_kwargs["fields"])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_publication_start__bot_api(self, mock_send):
        """Should use Bot API with required fields."""
        start_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        notify_slack_of_publication_start(self.bundle, start_time, self.inspect_url)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        self.assertEqual(call_kwargs["bundle"], self.bundle)
        self.assertEqual(call_kwargs["text"], "Publishing the bundle has started")
        self.assertEqual(call_kwargs["color"], "warning")  # Amber

        fields = call_kwargs["fields"]
        self.assertEqual(fields[0]["title"], "Bundle Name")
        self.assertIn("First Bundle", fields[0]["value"])
        self.assertIn(self.inspect_url, fields[0]["value"])

        self.assertIn({"title": "Publish Type", "value": "Manual", "short": True}, fields)
        self.assertIn({"title": "Scheduled Start", "value": "17/02/2026 - 10:00:00", "short": True}, fields)
        self.assertIn({"title": "Page Count", "value": "1", "short": True}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_publish_end__bot_api(self, mock_send):
        """Should use Bot API with required fields."""
        start_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        end_time = datetime(2026, 2, 17, 10, 0, 1, 234000, tzinfo=UTC)
        pages_published = 1

        notify_slack_of_publish_end(self.bundle, start_time, end_time, pages_published, self.inspect_url)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        self.assertEqual(call_kwargs["bundle"], self.bundle)
        self.assertEqual(call_kwargs["text"], "Publishing the bundle has ended")
        self.assertEqual(call_kwargs["color"], "good")  # Green

        fields = call_kwargs["fields"]
        self.assertEqual(fields[0]["title"], "Bundle Name")
        self.assertIn("First Bundle", fields[0]["value"])
        self.assertIn(self.inspect_url, fields[0]["value"])

        self.assertIn({"title": "Publish Type", "value": "Manual", "short": True}, fields)
        self.assertIn({"title": "Publish Start", "value": "17/02/2026 - 10:00:00", "short": True}, fields)
        self.assertIn({"title": "Publish End", "value": "17/02/2026 - 10:00:01", "short": True}, fields)
        self.assertIn({"title": "Duration", "value": "1.234 seconds", "short": True}, fields)
        self.assertIn({"title": "Page Count", "value": "1", "short": True}, fields)
        self.assertIn({"title": "Pages Published", "value": "1", "short": True}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_bundle_pre_publish__bot_api(self, mock_send):
        """Should send pre-publish notification with required fields."""
        scheduled_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        notify_slack_of_bundle_pre_publish(self.bundle, scheduled_time)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        self.assertEqual(call_kwargs["bundle"], self.bundle)
        self.assertEqual(call_kwargs["text"], "Preparing bundle for publication")
        self.assertEqual(call_kwargs["color"], "warning")  # Amber

        fields = call_kwargs["fields"]
        self.assertEqual(fields[0]["title"], "Bundle Name")
        self.assertIn("First Bundle", fields[0]["value"])
        self.assertIn(self.bundle.full_inspect_url, fields[0]["value"])

        self.assertIn({"title": "Publish Start", "value": "17/02/2026 - 10:00:00", "short": True}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_bundle_pre_publish__no_channel_configured(self, mock_send):
        """Should return early if no channel is configured."""
        scheduled_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        notify_slack_of_bundle_pre_publish(self.bundle, scheduled_time)
        mock_send.assert_not_called()


class SlackNotificationsWebhookTestCase(TestCase):
    """Tests for backward compatibility with webhook notifications."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="First Bundle", bundled_pages=[StatisticalArticlePageFactory()])
        cls.user = UserFactory(first_name="Publishing", last_name="Officer")
        request = RequestFactory().get("/")
        cls.inspect_url = request.build_absolute_uri(reverse("bundle:inspect", args=(cls.bundle.pk,)))

    def setUp(self):
        self.mock_response = Mock()
        self.mock_response.status_code = HTTPStatus.OK
        self.mock_response.body = ""

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk", SLACK_BOT_TOKEN=None)
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_status_change__webhook_fallback(self, mock_client):
        """Should use webhook when Bot API is not configured."""
        mock_client.return_value.send.return_value = self.mock_response

        self.bundle.status = BundleStatus.IN_REVIEW
        notify_slack_of_status_change(self.bundle, BundleStatus.DRAFT.label, self.user)

        mock_client.return_value.send.assert_called_once()
        call_kwargs = mock_client.return_value.send.call_args[1]

        self.assertEqual(call_kwargs["text"], "Bundle status changed")
        self.assertListEqual(
            call_kwargs["attachments"][0]["fields"],
            [
                {"title": "Title", "value": "First Bundle", "short": True},
                {"title": "Changed by", "value": "Publishing Officer", "short": True},
                {"title": "Old status", "value": BundleStatus.DRAFT.label, "short": True},
                {"title": "New status", "value": BundleStatus.IN_REVIEW.label, "short": True},
            ],
        )

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk", SLACK_BOT_TOKEN=None)
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_status_change__error_logging(self, mock_client):
        """Should log error if Slack request fails."""
        with self.assertLogs("cms.bundles") as logs_recorder:
            self.mock_response.status_code = HTTPStatus.BAD_REQUEST
            self.mock_response.body = "Error message"
            mock_client.return_value.send.return_value = self.mock_response

            self.bundle.status = BundleStatus.IN_REVIEW
            notify_slack_of_status_change(self.bundle, BundleStatus.DRAFT.label, self.user, self.inspect_url)
            call_kwargs = mock_client.return_value.send.call_args[1]
            self.assertListEqual(
                call_kwargs["attachments"][0]["fields"],
                [
                    {"title": "Title", "value": "First Bundle", "short": True},
                    {"title": "Changed by", "value": "Publishing Officer", "short": True},
                    {"title": "Old status", "value": BundleStatus.DRAFT.label, "short": True},
                    {"title": "New status", "value": BundleStatus.IN_REVIEW.label, "short": True},
                    {"title": "Link", "value": self.inspect_url, "short": False},
                ],
            )

            self.assertIn("Unable to notify Slack of bundle status change: Error message", logs_recorder.output[0])

    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_status_change__no_webhook_url(self, mock_client):
        """Should return early if no webhook URL is configured."""
        notify_slack_of_status_change(self.bundle, BundleStatus.DRAFT, self.user)
        mock_client.assert_not_called()

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_publication_start__with_release_calendar(self, mock_send):
        """Should include release calendar URL as example page."""
        release_page = ReleaseCalendarPageFactory()
        bundle = BundleFactory(name="Release Bundle", release_calendar_page=release_page)
        start_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)

        notify_slack_of_publication_start(bundle, start_time, url=self.inspect_url)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        fields = call_kwargs["fields"]
        self.assertIn({"title": "Publish Type", "value": "Release Calendar", "short": True}, fields)

        # Check that example page field is present with release calendar URL
        example_page_field = next((f for f in fields if f["title"] == "Example Page"), None)
        self.assertIsNotNone(example_page_field)
        self.assertEqual(example_page_field["value"], release_page.full_url)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_publication_start__no_channel_configured(self, mock_send):
        """Should return early if no channel is configured."""
        start_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        notify_slack_of_publication_start(self.bundle, start_time)
        mock_send.assert_not_called()

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_publish_end__with_scheduled_bundle(self, mock_send):
        """Should show Scheduled publish type for bundle with publication_date."""
        bundle = BundleFactory(
            name="Scheduled Bundle",
            publication_date=datetime(2026, 2, 17, 9, 30, 0, tzinfo=UTC),
            bundled_pages=[StatisticalArticlePageFactory()],
        )
        start_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        end_time = datetime(2026, 2, 17, 10, 0, 2, tzinfo=UTC)

        notify_slack_of_publish_end(bundle, start_time, end_time, 1, url=self.inspect_url)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        fields = call_kwargs["fields"]
        self.assertIn({"title": "Publish Type", "value": "Scheduled", "short": True}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_publish_end__no_channel_configured(self, mock_send):
        """Should return early if no channel is configured."""
        start_time = datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC)
        end_time = datetime(2026, 2, 17, 10, 0, 1, tzinfo=UTC)
        notify_slack_of_publish_end(self.bundle, start_time, end_time, 1)
        mock_send.assert_not_called()


class HelperFunctionsTestCase(TestCase):
    """Tests for Slack notification helper functions."""

    def test_get_publish_type__release_calendar(self):
        """Should return 'Release Calendar' when bundle has release_calendar_page_id."""
        release_page = ReleaseCalendarPageFactory()
        bundle = BundleFactory(release_calendar_page=release_page)
        self.assertEqual(_get_publish_type(bundle), "Release Calendar")

    def test_get_publish_type__scheduled(self):
        """Should return 'Scheduled' when bundle has publication_date."""
        bundle = BundleFactory(publication_date=datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC))
        self.assertEqual(_get_publish_type(bundle), "Scheduled")

    def test_get_publish_type__manual(self):
        """Should return 'Manual' when bundle has neither."""
        bundle = BundleFactory(publication_date=None, release_calendar_page=None)
        self.assertEqual(_get_publish_type(bundle), "Manual")

    def test_format_publish_datetime(self):
        """Should format datetime as DD/MM/YYYY - HH:MM:SS."""
        dt = datetime(2026, 2, 17, 14, 30, 45, tzinfo=UTC)
        formatted = _format_publish_datetime(dt)
        self.assertEqual(formatted, "17/02/2026 - 14:30:45")

    def test_get_example_page_url__release_calendar(self):
        """Should return release calendar URL when bundle has release_calendar_page_id."""
        release_page = ReleaseCalendarPageFactory()
        bundle = BundleFactory(release_calendar_page=release_page)
        url = _get_example_page_url(bundle)
        self.assertEqual(url, release_page.full_url)

    def test_get_example_page_url__first_page(self):
        """Should return first bundled page URL when no release calendar."""
        page = StatisticalArticlePageFactory()
        bundle = BundleFactory(bundled_pages=[page], release_calendar_page=None)
        url = _get_example_page_url(bundle)
        self.assertIsNotNone(url)
        self.assertIn(page.slug, url)

    def test_get_example_page_url__no_pages(self):
        """Should return None when no pages available."""
        bundle = BundleFactory(bundled_pages=[], release_calendar_page=None)
        url = _get_example_page_url(bundle)
        self.assertIsNone(url)

    def test_get_bundle_notification_context(self):
        """Should return dict with publish_type, page_count, and example_page_url."""
        page1 = StatisticalArticlePageFactory()
        page2 = StatisticalArticlePageFactory()
        bundle = BundleFactory(
            bundled_pages=[page1, page2],
            publication_date=datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC),
        )

        context = _get_bundle_notification_context(bundle)

        self.assertEqual(context["publish_type"], "Scheduled")
        self.assertEqual(context["page_count"], 2)
        self.assertIsNotNone(context["example_page_url"])
        self.assertIn(page1.slug, context["example_page_url"])


class BundleFailureNotificationTestCase(TestCase):
    """Tests for bundle failure notifications."""

    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Failed Bundle", bundled_pages=[StatisticalArticlePageFactory()])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__pre_publish_failed(self, mock_get_client):
        """Should send failure notification for pre-publish failure."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1503435956.000247"}
        mock_get_client.return_value = mock_client

        notify_slack_of_bundle_failure(
            bundle=self.bundle,
            failure_type="pre_publish_failed",
            exception_message="Page 'Test Page' is not ready to publish",
            alert_type="Warning",
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["text"], "Bundle failed to enter Pre-publish state")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "danger")
        self.assertFalse(call_kwargs["unfurl_links"])
        self.assertFalse(call_kwargs["unfurl_media"])

        fields = call_kwargs["attachments"][0]["fields"]
        self.assertEqual(fields[0]["title"], "Bundle Name")
        self.assertIn("Failed Bundle", fields[0]["value"])
        self.assertIn({"title": "Publish Type", "value": "Manual", "short": True}, fields)
        self.assertIn({"title": "Alert Type", "value": "Warning", "short": True}, fields)
        self.assertIn(
            {"title": "Exception", "value": "Page 'Test Page' is not ready to publish", "short": False}, fields
        )

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__publication_failed_critical(self, mock_get_client):
        """Should send critical alert when all pages fail to publish."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1503435956.000247"}
        mock_get_client.return_value = mock_client

        notify_slack_of_bundle_failure(
            bundle=self.bundle,
            failure_type="publication_failed",
            exception_message="3 of 3 page(s) failed to publish",
            alert_type="Critical",
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        self.assertEqual(call_kwargs["text"], "Bundle Publication Failure Detected")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "danger")

        fields = call_kwargs["attachments"][0]["fields"]
        self.assertIn({"title": "Alert Type", "value": "Critical", "short": True}, fields)
        self.assertIn({"title": "Exception", "value": "3 of 3 page(s) failed to publish", "short": False}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__publication_failed_partial(self, mock_get_client):
        """Should send fail alert when some pages fail to publish."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1503435956.000247"}
        mock_get_client.return_value = mock_client

        notify_slack_of_bundle_failure(
            bundle=self.bundle,
            failure_type="publication_failed",
            exception_message="1 of 3 page(s) failed to publish",
            alert_type="Fail",
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        fields = call_kwargs["attachments"][0]["fields"]
        self.assertIn({"title": "Alert Type", "value": "Fail", "short": True}, fields)
        self.assertIn({"title": "Exception", "value": "1 of 3 page(s) failed to publish", "short": False}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__with_scheduled_bundle(self, mock_get_client):
        """Should show correct publish type for scheduled bundles."""
        bundle = BundleFactory(
            name="Scheduled Bundle",
            publication_date=datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC),
            bundled_pages=[StatisticalArticlePageFactory()],
        )
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1503435956.000247"}
        mock_get_client.return_value = mock_client

        notify_slack_of_bundle_failure(
            bundle=bundle,
            failure_type="publication_failed",
            exception_message="Test error",
            alert_type="Critical",
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        fields = call_kwargs["attachments"][0]["fields"]
        self.assertIn({"title": "Publish Type", "value": "Scheduled", "short": True}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__no_channel_configured(self, mock_get_client):
        """Should return early if no channel is configured."""
        notify_slack_of_bundle_failure(
            bundle=self.bundle,
            failure_type="publication_failed",
            exception_message="Test error",
            alert_type="Critical",
        )
        mock_get_client.assert_not_called()

    @override_settings(SLACK_BOT_TOKEN=None, SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__no_client(self, mock_get_client):
        """Should return early with warning if client is not configured."""
        mock_get_client.return_value = None

        with self.assertLogs("cms.bundles", level="WARNING") as logs:
            notify_slack_of_bundle_failure(
                bundle=self.bundle,
                failure_type="publication_failed",
                exception_message="Test error",
                alert_type="Critical",
            )
            self.assertIn("Slack Bot API client not configured", logs.output[0])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__slack_api_error(self, mock_get_client):
        """Should log exception if Slack API call fails."""
        mock_client = Mock()
        mock_client.chat_postMessage.side_effect = SlackApiError("invalid_auth", response={"error": "invalid_auth"})
        mock_get_client.return_value = mock_client

        with self.assertLogs("cms.bundles", level="ERROR") as logs:
            notify_slack_of_bundle_failure(
                bundle=self.bundle,
                failure_type="publication_failed",
                exception_message="Test error",
                alert_type="Critical",
            )
            self.assertIn("Failed to send/update Slack message", logs.output[0])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack.get_slack_client")
    def test_notify_bundle_failure__does_not_update_slack_notification_ts(self, mock_get_client):
        """Should not store message timestamp for failure notifications."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1503435956.000247"}
        mock_get_client.return_value = mock_client

        original_ts = self.bundle.slack_notification_ts

        notify_slack_of_bundle_failure(
            bundle=self.bundle,
            failure_type="publication_failed",
            exception_message="Test error",
            alert_type="Critical",
        )

        # Verify timestamp was NOT updated
        self.bundle.refresh_from_db()
        self.assertEqual(self.bundle.slack_notification_ts, original_ts)


class NotifyDatasetAPIFailureTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.page = StatisticalArticlePageFactory(title="Test Page")

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_dataset_api_failure__with_page(self, mock_get_client):
        """Should send notification with page context."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_get_client.return_value = mock_client

        notify_slack_of_dataset_api_failure(
            page=self.page,
            exception_message="Timeout when fetching dataset",
            alert_type="Warning",
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]
        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["text"], "Data API Call Failure")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "danger")
        self.assertFalse(call_kwargs["unfurl_links"])
        self.assertFalse(call_kwargs["unfurl_media"])

        # Check fields
        fields = call_kwargs["attachments"][0]["fields"]
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0]["title"], "Page Name")
        self.assertIn("Test Page", fields[0]["value"])
        self.assertEqual(fields[1]["title"], "Alert Type")
        self.assertEqual(fields[1]["value"], "Warning")
        self.assertEqual(fields[2]["title"], "Exception")
        self.assertEqual(fields[2]["value"], "Timeout when fetching dataset")

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_dataset_api_failure__without_page(self, mock_get_client):
        """Should send notification without page context."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_get_client.return_value = mock_client

        notify_slack_of_dataset_api_failure(
            page=None,
            exception_message="Server error: HTTP 500",
            alert_type="Critical",
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        # Check fields - should not have page field
        fields = call_kwargs["attachments"][0]["fields"]
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0]["title"], "Alert Type")
        self.assertEqual(fields[0]["value"], "Critical")
        self.assertEqual(fields[1]["title"], "Exception")
        self.assertEqual(fields[1]["value"], "Server error: HTTP 500")

    @override_settings(SLACK_NOTIFICATION_CHANNEL="")
    def test_notify_dataset_api_failure__no_channel_configured(self):
        """Should not send notification when channel is not configured."""
        result = notify_slack_of_dataset_api_failure(
            page=None,
            exception_message="Test error",
            alert_type="Warning",
        )
        self.assertIsNone(result)

    @override_settings(SLACK_BOT_TOKEN=None, SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_dataset_api_failure__no_bot_token(self, mock_get_client):
        """Should not send notification when bot token is not configured."""
        mock_get_client.return_value = None

        with self.assertLogs("cms.bundles", level="WARNING") as logs:
            notify_slack_of_dataset_api_failure(
                page=None,
                exception_message="Test error",
                alert_type="Warning",
            )
            self.assertIn("Slack Bot API client not configured", logs.output[0])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_dataset_api_failure__slack_api_error(self, mock_get_client):
        """Should log error when Slack API call fails."""
        mock_client = Mock()
        mock_client.chat_postMessage.side_effect = Exception("Slack API error")
        mock_get_client.return_value = mock_client

        with self.assertLogs("cms.bundles", level="ERROR") as logs:
            notify_slack_of_dataset_api_failure(
                page=None,
                exception_message="Test error",
                alert_type="Warning",
            )
            self.assertIn("Failed to send dataset API failure notification", logs.output[0])


class NotifyThirdPartyAPIFailureTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.bundle = BundleFactory(name="Test Bundle")
        cls.page = StatisticalArticlePageFactory(title="Test Page")

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_third_party_api_failure__with_bundle(self, mock_get_client):
        """Should send notification with bundle context."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_get_client.return_value = mock_client

        notify_slack_of_third_party_api_failure(
            service_name="Bundle API",
            exception_message="HTTP 500 error: Internal Server Error",
            alert_type="Critical",
            bundle=self.bundle,
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]
        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["text"], "API Call Failure to Bundle API failed")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "danger")
        self.assertFalse(call_kwargs["unfurl_links"])
        self.assertFalse(call_kwargs["unfurl_media"])

        # Check fields
        fields = call_kwargs["attachments"][0]["fields"]
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0]["title"], "Bundle Name")
        self.assertIn("Test Bundle", fields[0]["value"])
        self.assertEqual(fields[1]["title"], "Alert Type")
        self.assertEqual(fields[1]["value"], "Critical")
        self.assertEqual(fields[2]["title"], "Exception")
        self.assertEqual(fields[2]["value"], "HTTP 500 error: Internal Server Error")

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_third_party_api_failure__with_page(self, mock_get_client):
        """Should send notification with page context."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_get_client.return_value = mock_client

        notify_slack_of_third_party_api_failure(
            service_name="Custom API",
            exception_message="Connection timeout",
            alert_type="Warning",
            page=self.page,
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        # Check fields
        fields = call_kwargs["attachments"][0]["fields"]
        self.assertEqual(len(fields), 3)
        self.assertEqual(fields[0]["title"], "Page Name")
        self.assertIn("Test Page", fields[0]["value"])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_third_party_api_failure__without_context(self, mock_get_client):
        """Should send notification without bundle or page context."""
        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_get_client.return_value = mock_client

        notify_slack_of_third_party_api_failure(
            service_name="External Service",
            exception_message="Network error",
            alert_type="Warning",
        )

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        # Check fields - should only have alert type and exception
        fields = call_kwargs["attachments"][0]["fields"]
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0]["title"], "Alert Type")
        self.assertEqual(fields[1]["title"], "Exception")

    @override_settings(SLACK_NOTIFICATION_CHANNEL="")
    def test_notify_third_party_api_failure__no_channel_configured(self):
        """Should not send notification when channel is not configured."""
        result = notify_slack_of_third_party_api_failure(
            service_name="Test API",
            exception_message="Test error",
            alert_type="Warning",
        )
        self.assertIsNone(result)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.api_failures.get_slack_client")
    def test_notify_third_party_api_failure__slack_api_error(self, mock_get_client):
        """Should log error when Slack API call fails."""
        mock_client = Mock()
        mock_client.chat_postMessage.side_effect = Exception("Slack API error")
        mock_get_client.return_value = mock_client

        with self.assertLogs("cms.bundles", level="ERROR") as logs:
            notify_slack_of_third_party_api_failure(
                service_name="Bundle API",
                exception_message="Test error",
                alert_type="Critical",
            )
            self.assertIn("Failed to send third-party API failure notification", logs.output[0])
