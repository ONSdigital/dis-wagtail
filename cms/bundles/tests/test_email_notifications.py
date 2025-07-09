from unittest.mock import patch

from django.core import mail
from django.template import TemplateDoesNotExist
from django.test import TestCase

from cms.bundles.models import Bundle, BundleTeam
from cms.bundles.notifications.email import _send_bundle_email
from cms.bundles.tests.factories import BundleFactory
from cms.teams.tests.factories import TeamFactory
from cms.users.tests.factories import UserFactory


class TestEmailNotifications(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.email_alternatives_messages = ["Perfectly fine plain text message", "<p>Perfectly fine HTML message</p>"]

    def setUp(self):
        """Set up the test case."""
        # Clear the mail outbox before each test
        mail.outbox = []

    def test_that_an_error_is_logged_when_preview_team_member_has_no_email(self):
        """Test that an error is logged when a notification email is sent to a preview team
        and one of the members doesn't have an email.
        """
        bundle = BundleFactory(in_review=True, name="Preview Bundle")
        preview_team = TeamFactory()
        user_without_email = UserFactory(email="")
        preview_team.users.add(user_without_email)

        with (
            patch("cms.bundles.notifications.email.render_to_string") as mock_render,
        ):
            mock_render.side_effect = self.email_alternatives_messages
            with self.assertLogs("cms.bundles.notifications.email", level="ERROR") as log:
                _send_bundle_email(
                    bundle=bundle,
                    team=preview_team,
                    email_template_name="example_template",
                    subject="Test Subject",
                )

        self.assertEqual(len(log.records), 1, "Expected exactly one log record.")

        record = log.records[0]
        self.assertEqual(record.user_id, user_without_email.id)
        self.assertEqual(record.team_name, preview_team.name)
        self.assertEqual(record.bundle_name, bundle.name)
        self.assertEqual(record.email_subject, "Test Subject")

        self.assertEqual(len(mail.outbox), 0)

    def test_error_is_logged_when_email_sending_fails(self):
        """Ensure an error is logged if send_mail raises an exception."""
        preview_team = TeamFactory(name="Preview Team")
        bundle = BundleFactory(in_review=True, name="Preview Bundle")
        previewer = UserFactory()
        another_previewer = UserFactory()
        preview_team.users.add(previewer, another_previewer)

        with (
            patch("cms.bundles.notifications.email.send_mail") as mock_send_mail,
            patch("cms.bundles.notifications.email.render_to_string") as mock_render,
        ):
            mock_send_mail.side_effect = Exception("SMTP error")
            mock_render.side_effect = self.email_alternatives_messages
            with self.assertLogs("cms.bundles.notifications.email", level="ERROR") as log:
                _send_bundle_email(
                    bundle=bundle,
                    team=preview_team,
                    email_template_name="non_existent",
                    subject="Test Subject",
                )

        self.assertEqual(len(log.records), 1, "Expected exactly one log record.")

        record = log.records[0]
        self.assertEqual(record.msg, "Failed to send bundle notification email")
        self.assertEqual(record.team_name, preview_team.name)
        self.assertEqual(record.bundle_name, bundle.name)
        self.assertEqual(record.email_subject, "Test Subject")
        self.assertEqual(sorted(record.recipients), sorted([previewer.email, another_previewer.email]))
        self.assertEqual(record.error_message, "SMTP error")

        self.assertEqual(len(mail.outbox), 0)

    def test_send_bundle_email_logs_and_re_raises_exception_when_plain_text_template_does_not_exist(self):
        """Test that an error is logged and an exception is re-raised
        when the plain text email template does not exist.
        """
        bundle = Bundle.objects.create(name="Test Bundle")
        preview_team = TeamFactory(name="Test Team")
        _bundle_team = BundleTeam(parent=bundle, team=preview_team)

        with (
            patch("cms.bundles.notifications.email.render_to_string") as mock_render,
            self.assertRaises(TemplateDoesNotExist),
        ):
            mock_render.side_effect = TemplateDoesNotExist(
                "bundles/notification_emails/plain_text_variant/non_existent.txt"
            )

            with self.assertLogs("cms.bundles.notifications.email", level="ERROR") as log:
                _send_bundle_email(
                    bundle=bundle,
                    team=preview_team,
                    email_template_name="non_existent",
                    subject="Test Subject",
                )
            self.assertEqual(len(log.records), 1, "Expected exactly one log record.")
            self.assertEqual(log.records[0].msg, "Plain text email template not found")

    def test_html_email_variant_is_not_sent_when_the_template_is_not_found(self):
        """Test that if the HTML email template isn't found, then only the plain text variant is sent."""
        bundle = Bundle.objects.create(name="Test Bundle")
        team = TeamFactory(name="Test Team")
        user = UserFactory()
        team.users.add(user)
        _bundle_team = BundleTeam(parent=bundle, team=team)

        with patch("cms.bundles.notifications.email.render_to_string") as mock_render:
            mock_render.side_effect = ["Perfectly fine plain text message", Exception("Failed to render HTML template")]
            with self.assertLogs("cms.bundles.notifications.email", level="WARN") as log:
                _send_bundle_email(
                    bundle=bundle,
                    team=team,
                    email_template_name="exists_only_in_plain_text_variant",
                    subject="Test Subject",
                )

        self.assertEqual(len(log.records), 1, "Expected exactly one log record.")
        self.assertEqual(log.records[0].msg, "Failed to generate HTML email message")

        self.assertEqual(len(mail.outbox), 1)
        email_object = mail.outbox[0]
        self.assertEqual(email_object.subject, "Test Subject")
        self.assertEqual(email_object.body, "Perfectly fine plain text message")

    def test_send_bundle_plain_text_and_html_alternatives_happy_path(self):
        """Test that both plain text and HTML email templates are rendered and sent."""
        bundle = Bundle.objects.create(name="Test Bundle")
        team = TeamFactory(name="Test Team")
        user = UserFactory()
        team.users.add(user)
        _bundle_team = BundleTeam(parent=bundle, team=team)

        with patch("cms.bundles.notifications.email.render_to_string") as mock_render:
            mock_render.side_effect = self.email_alternatives_messages

            _send_bundle_email(
                bundle=bundle,
                team=team,
                email_template_name="test_template",
                subject="Test Subject",
            )

            self.assertEqual(len(mail.outbox), 1)
            email_object = mail.outbox[0]
            self.assertEqual(email_object.subject, "Test Subject")
            self.assertIn("Perfectly fine plain text message", email_object.body)
            self.assertIn("<p>Perfectly fine HTML message</p>", email_object.alternatives[0].content)
