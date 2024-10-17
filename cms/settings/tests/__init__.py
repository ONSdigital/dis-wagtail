from django.test import TestCase


class SecurityHeadersTestCase(TestCase):
    def test_referrer_policy(self):
        response = self.client.get("/")
        self.assertEqual(response["Referrer-Policy"], "no-referrer-when-downgrade")
