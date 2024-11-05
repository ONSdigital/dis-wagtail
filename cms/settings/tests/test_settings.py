from datetime import datetime

from django.template import Context, Template
from django.test import TestCase


class SettingsTestCase(TestCase):
    """Tests for the Referrer-Policy header."""

    def test_referrer_policy(self):
        """Test that we have a Referrer-Policy header."""
        response = self.client.get("/")
        self.assertEqual(response["Referrer-Policy"], "no-referrer-when-downgrade")

    def test_date_format(self):
        """Test that DATETIME_FORMAT is our preferred one."""
        template = Template("{{ date|date:'DATETIME_FORMAT' }}")
        date = datetime(2024, 11, 1, 13, 0)
        self.assertEqual(template.render(Context({"date": date})), "1 November 2024 1:00p.m.")
