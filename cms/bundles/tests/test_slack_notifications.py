from http import HTTPStatus
from unittest.mock import Mock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from slack_sdk.errors import SlackApiError

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.notifications.slack import (
    _send_and_update_message,
    get_slack_client,
    notify_slack_of_publication_start,
    notify_slack_of_publish_end,
    notify_slack_of_status_change,
)
from cms.bundles.tests.factories import BundleFactory
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
        """Should use Bot API when fully configured."""
        notify_slack_of_publication_start(self.bundle, self.user, self.inspect_url)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        self.assertEqual(call_kwargs["bundle"], self.bundle)
        self.assertEqual(call_kwargs["text"], "Starting bundle publication")
        self.assertEqual(call_kwargs["color"], "good")
        self.assertIn({"title": "Title", "value": "First Bundle", "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "User", "value": "Publishing Officer", "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "Pages", "value": 1, "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "Link", "value": self.inspect_url, "short": False}, call_kwargs["fields"])

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token", SLACK_NOTIFICATION_CHANNEL="C024BE91L")
    @patch("cms.bundles.notifications.slack._send_and_update_message")
    def test_notify_slack_of_publish_end__bot_api(self, mock_send):
        """Should use Bot API when fully configured."""
        notify_slack_of_publish_end(self.bundle, 1.234, self.user, self.inspect_url)

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]

        self.assertEqual(call_kwargs["bundle"], self.bundle)
        self.assertEqual(call_kwargs["text"], "Finished bundle publication")
        self.assertEqual(call_kwargs["color"], "good")
        self.assertIn({"title": "Title", "value": "First Bundle", "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "User", "value": "Publishing Officer", "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "Pages", "value": 1, "short": True}, call_kwargs["fields"])
        self.assertIn({"title": "Total time", "value": "1.234 seconds"}, call_kwargs["fields"])
        self.assertIn({"title": "Link", "value": self.inspect_url, "short": False}, call_kwargs["fields"])


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

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk", SLACK_BOT_TOKEN=None)
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publication_start__webhook_fallback(self, mock_client):
        """Should use webhook when Bot API is not configured."""
        mock_client.return_value.send.return_value = self.mock_response

        notify_slack_of_publication_start(self.bundle, self.user, self.inspect_url)

        mock_client.return_value.send.assert_called_once()
        call_kwargs = mock_client.return_value.send.call_args[1]

        self.assertEqual(call_kwargs["text"], "Starting bundle publication")
        self.assertListEqual(
            call_kwargs["attachments"][0]["fields"],
            [
                {"title": "Title", "value": "First Bundle", "short": True},
                {"title": "User", "value": "Publishing Officer", "short": True},
                {"title": "Pages", "value": 1, "short": True},
                {"title": "Link", "value": self.inspect_url, "short": False},
            ],
        )

    def test_notify_slack_of_publication_start__no_webhook_url(self):
        """Should return early if no webhook URL is configured."""
        with patch("slack_sdk.webhook.WebhookClient") as mock_client:
            notify_slack_of_publication_start(self.bundle, self.user)
            mock_client.assert_not_called()

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk", SLACK_BOT_TOKEN=None)
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publish_start__error_logging(self, mock_client):
        """Should log error if Slack request fails."""
        with self.assertLogs("cms.bundles") as logs_recorder:
            self.mock_response.status_code = HTTPStatus.BAD_REQUEST
            self.mock_response.body = "Error message"
            mock_client.return_value.send.return_value = self.mock_response

            notify_slack_of_publication_start(self.bundle, self.user)

            self.assertIn("Unable to notify Slack of bundle publication start: Error message", logs_recorder.output[0])

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk", SLACK_BOT_TOKEN=None)
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publish_end__webhook_fallback(self, mock_client):
        """Should use webhook when Bot API is not configured."""
        mock_client.return_value.send.return_value = self.mock_response

        notify_slack_of_publish_end(self.bundle, 1.234, self.user, self.inspect_url)

        mock_client.return_value.send.assert_called_once()
        call_kwargs = mock_client.return_value.send.call_args[1]

        self.assertEqual(call_kwargs["text"], "Finished bundle publication")
        fields = call_kwargs["attachments"][0]["fields"]

        self.assertListEqual(
            fields,
            [
                {"title": "Title", "value": "First Bundle", "short": True},
                {"title": "User", "value": "Publishing Officer", "short": True},
                {"title": "Pages", "value": 1, "short": True},
                {"title": "Total time", "value": "1.234 seconds"},
                {"title": "Link", "value": self.inspect_url, "short": False},
            ],
        )
        self.assertEqual(len(fields), 5)  # Including URL and elapsed time

    def test_notify_slack_of_publish_end__no_webhook_url(self):
        """Should return early if no webhook URL is configured."""
        with patch("slack_sdk.webhook.WebhookClient") as mock_client:
            notify_slack_of_publish_end(self.bundle, 1.234, self.user)
            mock_client.assert_not_called()

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk", SLACK_BOT_TOKEN=None)
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publish_end__error_logging(self, mock_client):
        """Should log error if Slack request fails."""
        with self.assertLogs("cms.bundles") as logs_recorder:
            self.mock_response.status_code = HTTPStatus.BAD_REQUEST
            self.mock_response.body = "Error message"
            mock_client.return_value.send.return_value = self.mock_response

            notify_slack_of_publish_end(self.bundle, 1.234, self.user, self.inspect_url)

            self.assertIn("Unable to notify Slack of bundle publication finish: Error message", logs_recorder.output[0])
