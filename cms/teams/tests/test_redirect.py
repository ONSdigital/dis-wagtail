from http import HTTPStatus

from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils


class TeamsRedirectTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

    def setUp(self):
        self.client.force_login(self.superuser)

    @override_settings(
        ALLOW_TEAM_MANAGEMENT=False,
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        FLORENCE_GROUPS_PATH="/florence/groups",
    )
    def test_teams_index_redirects_to_florence_when_sync_enabled(self):
        response = self.client.get(reverse("teams:index"))
        self.assertRedirects(response, "/florence/groups", fetch_redirect_response=False)

    @override_settings(
        ALLOW_TEAM_MANAGEMENT=False,
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        FLORENCE_GROUPS_PATH="/florence/groups",
    )
    def test_teams_subpath_redirects_to_florence_when_sync_enabled(self):
        response = self.client.get("/admin/teams/add/")
        self.assertRedirects(response, "/florence/groups", fetch_redirect_response=False)

    @override_settings(
        ALLOW_TEAM_MANAGEMENT=True,
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
    )
    def test_no_redirect_when_team_management_enabled(self):
        response = self.client.get(reverse("teams:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @override_settings(
        ALLOW_TEAM_MANAGEMENT=True,
        AWS_COGNITO_TEAM_SYNC_ENABLED=False,
    )
    def test_no_redirect_when_team_management_enabled_but_no_sync(self):
        response = self.client.get(reverse("teams:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @override_settings(
        ALLOW_TEAM_MANAGEMENT=False,
        AWS_COGNITO_TEAM_SYNC_ENABLED=False,
    )
    def test_no_redirect_when_cognito_sync_disabled(self):
        response = self.client.get(reverse("teams:index"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
