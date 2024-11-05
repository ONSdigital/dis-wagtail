from django.test import TestCase


class ReferrerPolicyTestCase(TestCase):
    """Tests for the Referrer-Policy header."""
    def test_referrer_policy(self):
        """Test that we have a Referrer-Policy header."""
        response = self.client.get("/")
        self.assertEqual(response["Referrer-Policy"], "no-referrer-when-downgrade")
