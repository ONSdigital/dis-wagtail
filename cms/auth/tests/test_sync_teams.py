# tests/management/test_sync_teams.py
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from cms.auth.tests.helpers import DummyResponse
from cms.teams.models import Team


class SyncTeamsCommandTests(TestCase):
    @override_settings(
        IDENTITY_API_BASE_URL="http://identity",
        ROLE_GROUP_IDS=["admin-role"],
    )
    @mock.patch("cms.teams.management.commands.sync_teams.requests.get")
    def test_creates_and_updates_teams(self, mock_get):
        # fake API response
        api_groups = {
            "groups": [
                {
                    "id": "team-1",
                    "name": "Team One",
                    "precedence": 1,
                    "creation_date": "2024-01-01T00:00:00",
                    "last_modified_date": "2024-01-02T00:00:00",
                }
            ]
        }
        mock_get.return_value = DummyResponse(api_groups)

        # run command
        call_command("sync_teams")
        self.assertTrue(Team.objects.filter(identifier="team-1", is_active=True).exists())

        # update Name + run again   →  Team updated
        api_groups["groups"][0]["name"] = "Team One - updated"
        mock_get.return_value = DummyResponse(api_groups)
        call_command("sync_teams")
        self.assertEqual(Team.objects.get(identifier="team-1").name, "Team One - updated")

    @override_settings(IDENTITY_API_BASE_URL="http://identity", ROLE_GROUP_IDS=[])
    @mock.patch("cms.teams.management.commands.sync_teams.requests.get")
    def test_dry_run_does_not_hit_db(self, mock_get):
        api_groups = {"groups": []}
        mock_get.return_value = DummyResponse(api_groups)
        with self.assertNumQueries(0):  # no write queries
            call_command("sync_teams", "--dry-run")
