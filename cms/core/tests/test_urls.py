from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, resolve, reverse


class PrivacyRouteGatingTests(TestCase):
    """The privacy support routes must only be registered when their feature flags are on."""

    @override_settings(CMS_PAGE_PRIVACY_CONTROLS_ENABLED=True)
    def test_frontend_login_route_registered_when_page_privacy_enabled(self):
        self.assertEqual(reverse("frontend_login_redirect"), "/auth/frontend-login")

        response = self.client.get("/auth/frontend-login")
        self.assertEqual(response.status_code, 302)

    @override_settings(CMS_PAGE_PRIVACY_CONTROLS_ENABLED=False)
    def test_frontend_login_route_absent_when_page_privacy_disabled(self):
        with self.assertRaises(NoReverseMatch):
            reverse("frontend_login_redirect")

        response = self.client.get("/auth/frontend-login")
        self.assertEqual(response.status_code, 404)

    @override_settings(CMS_COLLECTION_PRIVACY_CONTROLS_ENABLED=True)
    def test_documents_authenticate_route_registered_when_collection_privacy_enabled(self):
        url = reverse("wagtaildocs_authenticate_with_password", args=[1])
        self.assertEqual(url, "/documents/authenticate_with_password/1")

        match = resolve(url)
        self.assertEqual(match.view_name, "wagtaildocs_authenticate_with_password")

    @override_settings(CMS_COLLECTION_PRIVACY_CONTROLS_ENABLED=False)
    def test_documents_authenticate_route_absent_when_collection_privacy_disabled(self):
        with self.assertRaises(NoReverseMatch):
            reverse("wagtaildocs_authenticate_with_password", args=[1])

        # The path falls through to wagtail's catch-all page serving (which 404s, as
        # no page exists there) instead of the documents password view.
        match = resolve("/documents/authenticate_with_password/1")
        self.assertEqual(match.view_name, "wagtail_serve")

    @override_settings(CMS_PAGE_PRIVACY_CONTROLS_ENABLED=False, CMS_COLLECTION_PRIVACY_CONTROLS_ENABLED=False)
    def test_wagtail_builtin_privacy_routes_always_available(self):
        """Wagtail's own view-restriction routes are the fallback and must remain routable."""
        self.assertTrue(reverse("wagtailcore_login"))
        self.assertTrue(reverse("wagtailcore_authenticate_with_password", args=[1, 1]))
