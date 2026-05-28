# secretlint-disable
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from slack_sdk.errors import SlackApiError

from cms.core.slack import (
    get_slack_client,
    send_or_update_slack_message,
)


class SendOrUpdateMessageTestCase(TestCase):
    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token")
    @patch("cms.core.slack.get_slack_client")
    def test_send_new_message(self, mock_get_client):
        """A new message should be posted when a timestamp is not provided."""
        mock_client = Mock()
        mock_response = {"ok": True, "ts": "1503435956.000247"}
        mock_client.chat_postMessage.return_value = mock_response
        mock_get_client.return_value = mock_client

        message_ts = send_or_update_slack_message(
            text="This is a test message",
            channel="C024BE91L",
            color="good",
            fields=[{"title": "foo", "value": "bar", "short": True}],
        )

        self.assertEqual(message_ts, mock_response["ts"])

        mock_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["text"], "This is a test message")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "good")

        fields = call_kwargs["attachments"][0]["fields"]
        self.assertIn({"title": "foo", "value": "bar", "short": True}, fields)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token")
    @patch("cms.core.slack.get_slack_client")
    def test_update_existing_message(self, mock_get_client):
        """Should update existing message when a valid timestamp is provided."""
        mock_client = Mock()
        mock_response = {"ok": True, "ts": "1234567890.111111"}
        mock_client.chat_update.return_value = mock_response
        mock_get_client.return_value = mock_client

        message_ts = send_or_update_slack_message(
            text="This is a test message",
            channel="C024BE91L",
            color="good",
            fields=[{"title": "foo", "value": "bar", "short": True}],
            update_message_ts="1234567890.000000",
        )

        self.assertEqual(message_ts, mock_response["ts"])

        mock_client.chat_update.assert_called_once()
        call_kwargs = mock_client.chat_update.call_args[1]

        self.assertEqual(call_kwargs["ts"], "1234567890.000000")
        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["text"], "This is a test message")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "good")

        fields = call_kwargs["attachments"][0]["fields"]
        self.assertIn({"title": "foo", "value": "bar", "short": True}, fields)

    @patch("cms.core.slack.get_slack_client")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token")
    def test_update_existing_message_fallback_to_posting_new(self, mock_get_client):
        """Should update existing message when a valid timestamp is provided."""
        mock_client = Mock()
        mock_response = {"ok": True, "ts": "1234567890.111111"}

        # Raise an error when trying to update, simulating a case where the message to update is not found
        mock_client.chat_update.side_effect = SlackApiError("message_not_found", Mock())
        mock_client.chat_postMessage.return_value = mock_response
        mock_get_client.return_value = mock_client

        with self.assertLogs("cms.core.slack", level="ERROR") as logs:
            message_ts = send_or_update_slack_message(
                text="This is a test message",
                channel="C024BE91L",
                color="good",
                fields=[{"title": "foo", "value": "bar", "short": True}],
                update_message_ts="1234567890.000000",
            )
            self.assertIn("Failed to send/update Slack message: message_not_found", logs.output[0])

        self.assertEqual(message_ts, mock_response["ts"])

        mock_client.chat_update.assert_called_once()  # Assert that an update was attempted
        mock_client.chat_postMessage.assert_called_once()  # Check that it fell back to posting a new message
        call_kwargs = mock_client.chat_postMessage.call_args[1]

        self.assertEqual(call_kwargs["channel"], "C024BE91L")
        self.assertEqual(call_kwargs["text"], "This is a test message")
        self.assertEqual(call_kwargs["attachments"][0]["color"], "good")

        fields = call_kwargs["attachments"][0]["fields"]
        self.assertIn({"title": "foo", "value": "bar", "short": True}, fields)

    @patch("cms.core.slack.get_slack_client")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token")
    def test_update_existing_message_fallback_failure(self, mock_get_client):
        """Should update existing message when a valid timestamp is provided."""
        mock_client = Mock()
        # Raise an error when trying to update, simulating a case where the message to update is not found
        mock_client.chat_update.side_effect = SlackApiError("message_not_found", Mock())
        mock_client.chat_postMessage.side_effect = SlackApiError("post_failed", Mock())
        mock_get_client.return_value = mock_client

        with self.assertLogs("cms.core.slack", level="ERROR") as logs:
            message_ts = send_or_update_slack_message(
                text="This is a test message",
                channel="C024BE91L",
                color="good",
                fields=[{"title": "foo", "value": "bar", "short": True}],
                update_message_ts="1234567890.000000",
            )
            self.assertIn("Failed to send/update Slack message: message_not_found", logs.output[0])
            self.assertIn("Failed to create fallback Slack message", logs.output[1])

        self.assertIsNone(message_ts)

        mock_client.chat_update.assert_called_once()  # Assert that an update was attempted
        mock_client.chat_postMessage.assert_called_once()  # Check that it fell back to posting a new message

    @override_settings(SLACK_BOT_TOKEN=None)
    def test_log_message_if_token_is_not_configured(self):
        """Should log a message and skip sending if token is not configured, even if channel is provided."""
        with self.assertLogs("cms.core.slack", level="INFO") as logs:
            message_ts = send_or_update_slack_message(
                text="This is a test message",
                channel="C024BE91L",
                color="good",
                fields=[{"title": "foo", "value": "bar", "short": True}],
                update_message_ts="1234567890.000000",
            )
            self.assertIn("Skipping sending Slack message (token or channel not configured)", logs.output[0])
            self.assertEqual("This is a test message", logs.records[0].slack_message)
            self.assertEqual(
                [{"color": "good", "fields": [{"title": "foo", "value": "bar", "short": True}]}],
                logs.records[0].attachments,
            )

        self.assertIsNone(message_ts)

    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token")
    def test_log_message_if_channel_is_not_given(self):
        """Should log a message and skip sending if the message channel is None."""
        with self.assertLogs("cms.core.slack", level="INFO") as logs:
            message_ts = send_or_update_slack_message(
                text="This is a test message",
                channel=None,
                color="good",
                fields=[{"title": "foo", "value": "bar", "short": True}],
                update_message_ts="1234567890.000000",
            )
            self.assertIn("Skipping sending Slack message (token or channel not configured)", logs.output[0])
            self.assertEqual("This is a test message", logs.records[0].slack_message)
            self.assertEqual(
                [{"color": "good", "fields": [{"title": "foo", "value": "bar", "short": True}]}],
                logs.records[0].attachments,
            )

        self.assertIsNone(message_ts)


class GetSlackClientTestCase(TestCase):
    @override_settings(SLACK_BOT_TOKEN="xoxb-test-token")
    @patch("cms.core.slack.WebClient")
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
