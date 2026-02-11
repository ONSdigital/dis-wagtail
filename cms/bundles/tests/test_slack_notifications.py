from http import HTTPStatus
from unittest.mock import Mock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.notifications.slack import (
    notify_slack_of_publication_start,
    notify_slack_of_publish_end,
    notify_slack_of_status_change,
)
from cms.bundles.tests.factories import BundleFactory
from cms.users.tests.factories import UserFactory


class SlackNotificationsTestCase(TestCase):
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

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_status_change__happy_path(self, mock_client):
        """Should send notification with correct fields."""
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

    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_status_change__no_webhook_url(self, mock_client):
        """Should return early if no webhook URL is configured."""
        notify_slack_of_status_change(self.bundle, BundleStatus.DRAFT, self.user)
        mock_client.assert_not_called()

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
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

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publication_start__happy_path(self, mock_client):
        """Should send notification with correct fields."""
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

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publish_start__error_logging(self, mock_client):
        """Should log error if Slack request fails."""
        with self.assertLogs("cms.bundles") as logs_recorder:
            self.mock_response.status_code = HTTPStatus.BAD_REQUEST
            self.mock_response.body = "Error message"
            mock_client.return_value.send.return_value = self.mock_response

            notify_slack_of_publication_start(self.bundle, self.user)

            self.assertIn("Unable to notify Slack of bundle publication start: Error message", logs_recorder.output[0])

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publish_end__happy_path(self, mock_client):
        """Should send notification with correct fields."""
        mock_client.return_value.send.return_value = self.mock_response

        notify_slack_of_publish_end(self.bundle, 1.234, self.user, self.inspect_url)

        mock_client.return_value.send.assert_called_once()
        call_kwargs = mock_client.return_value.send.call_args[1]

        self.assertEqual(call_kwargs["text"], "Finished bundle publication")
        fields = call_kwargs["attachments"][0]["fields"]

        self.assertEqual(
            fields,
            [
                {"title": "Title", "value": "First Bundle", "short": True},
                {"title": "User", "value": "Publishing Officer", "short": True},
                {"title": "Total Pages", "value": 1, "short": True},
                {"title": "Published Pages", "value": 1, "short": True},
                {"title": "Total time", "value": "1.234 seconds"},
                {"title": "Link", "value": self.inspect_url, "short": False},
            ],
        )

    def test_notify_slack_of_publish_end__no_webhook_url(self):
        """Should return early if no webhook URL is configured."""
        with patch("slack_sdk.webhook.WebhookClient") as mock_client:
            notify_slack_of_publish_end(self.bundle, 1.234, self.user)
            mock_client.assert_not_called()

    @override_settings(SLACK_NOTIFICATIONS_WEBHOOK_URL="https://slack.ons.gov.uk")
    @patch("cms.bundles.notifications.slack.WebhookClient")
    def test_notify_slack_of_publish_end__error_logging(self, mock_client):
        """Should log error if Slack request fails."""
        with self.assertLogs("cms.bundles") as logs_recorder:
            self.mock_response.status_code = HTTPStatus.BAD_REQUEST
            self.mock_response.body = "Error message"
            mock_client.return_value.send.return_value = self.mock_response

            notify_slack_of_publish_end(self.bundle, 1.234, self.user, self.inspect_url)

            self.assertIn("Unable to notify Slack of bundle publication finish: Error message", logs_recorder.output[0])
