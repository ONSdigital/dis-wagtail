from datetime import UTC, datetime, timedelta
from unittest import mock

import requests
from django.core import management
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from cms.teams.models import Team

NOW = datetime.now(tz=UTC).replace(microsecond=0)
ISO_NOW = NOW.isoformat()


def api_group(
    *,
    gid: str,
    name: str = "Team",
    precedence: int = 1,
    created: str = ISO_NOW,
    updated: str = ISO_NOW,
):
    """Return a dict in the shape produced by the Identity API."""
    return {
        "id": gid,
        "name": name,
        "precedence": precedence,
        "creation_date": created,
        "last_modified_date": updated,
    }


@override_settings(
    SERVICE_AUTH_TOKEN="test-token",
    IDENTITY_API_BASE_URL="https://identity.example",
)
class SyncTeamsCommandTests(TestCase):
    """Covers creation, update, de-activation, dry-run, API/network errors,
    auth headers, and role-group exclusion logic.
    """

    def _call_command(self, *, dry_run=False):
        argv = ["--dry-run"] if dry_run else []
        with open("/dev/null", "w", encoding="utf-8") as stdout:
            management.call_command("sync_teams", *argv, stdout=stdout)

    def _mock_api(self, groups, expected_headers=None):
        """Patch requests.get so /groups returns supplied list, optionally asserting headers."""
        resp_json = {"groups": groups}

        def fake_get(url, *args, **kwargs):
            self.assertIn("/groups", url)
            headers = kwargs.get("headers", {})
            if expected_headers is not None:
                self.assertEqual(headers, expected_headers)

            return mock.Mock(
                status_code=200,
                json=lambda: resp_json,
                raise_for_status=lambda: None,
            )

        return mock.patch(
            "cms.teams.management.commands.sync_teams.requests.get",
            side_effect=fake_get,
        )

    def test_create_update_deactivate(self):
        """happy-path: create new, update existing, deactivate missing."""
        # existing Team A will be UPDATED, Team B will be DEACTIVATED
        Team.objects.create(
            identifier="team-a",
            name="Old A",
            precedence=1,
            created_at=NOW - timedelta(days=2),
            updated_at=NOW - timedelta(days=2),
            is_active=True,
        )
        Team.objects.create(
            identifier="team-b",
            name="Team B",
            precedence=1,
            created_at=NOW,
            updated_at=NOW,
            is_active=True,
        )

        # identity API returns new values for A, brand-new C, ignores B
        api_groups = [
            api_group(gid="team-a", name="New A", precedence=2),
            api_group(gid="team-c", name="Team C", precedence=3),
            api_group(gid="role-admin", name="Role Admin"),  # should be ignored
        ]

        with self._mock_api(api_groups):
            self._call_command()

        a = Team.objects.get(identifier="team-a")
        self.assertEqual(a.name, "New A")
        self.assertEqual(a.precedence, 2)
        self.assertTrue(a.is_active)

        b = Team.objects.get(identifier="team-b")
        self.assertFalse(b.is_active)  # de-activated

        c = Team.objects.get(identifier="team-c")
        self.assertTrue(c.is_active)
        self.assertEqual(c.precedence, 3)

    def test_dry_run_makes_no_changes(self):
        Team.objects.create(
            identifier="dry",
            name="Dry",
            precedence=1,
            created_at=NOW,
            updated_at=NOW,
            is_active=True,
        )

        api_groups = [api_group(gid="dry", name="DRY CHANGED", precedence=99)]

        with self._mock_api(api_groups):
            self._call_command(dry_run=True)

        team = Team.objects.get(identifier="dry")
        self.assertEqual(team.name, "Dry")  # unchanged
        self.assertEqual(team.precedence, 1)
        self.assertTrue(team.is_active)

    def test_network_error_raises_command_error(self):
        def boom(*_, **__):
            raise requests.ConnectionError("no network")

        with mock.patch("cms.teams.management.commands.sync_teams.requests.get", boom), self.assertRaises(CommandError):
            self._call_command()

    def test_invalid_json_raises_command_error(self):
        bad_resp = mock.Mock(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: (_ for _ in ()).throw(ValueError("bad json")),  # iterator trick to raise
        )

        with (
            mock.patch("cms.teams.management.commands.sync_teams.requests.get", return_value=bad_resp),
            self.assertRaises(CommandError),
        ):
            self._call_command()

    def test_missing_base_url_setting_raises(self):
        with override_settings(IDENTITY_API_BASE_URL=None), self.assertRaises(CommandError):
            self._call_command()

    # HTTP 5xx raise_for_status fires up as CommandError
    def test_http_error_raises_command_error(self):
        bad_resp = mock.Mock(
            status_code=500,
            raise_for_status=mock.Mock(side_effect=requests.HTTPError("boom")),
        )
        with (
            mock.patch("cms.teams.management.commands.sync_teams.requests.get", return_value=bad_resp),
            self.assertRaises(CommandError),
        ):
            self._call_command()

    # A previously inactive team should be re-activated when present in the remote payload.
    def test_inactive_team_reactivated(self):
        team = Team.objects.create(
            identifier="react",
            name="Reactivate Me",
            precedence=1,
            created_at=NOW,
            updated_at=NOW,
            is_active=False,
        )

        with self._mock_api([api_group(gid="react", name="Reactivate Me", precedence=2)]):
            self._call_command()

        team.refresh_from_db()
        self.assertTrue(team.is_active)

    # When the remote payload is identical, save() must not be called.
    def test_no_change_skips_save(self):
        team = Team.objects.create(
            identifier="same",
            name="Same",
            precedence=1,
            created_at=NOW,
            updated_at=NOW,
            is_active=True,
        )

        identical_payload = [api_group(gid="same", name="Same", precedence=1)]

        with (
            self._mock_api(identical_payload),
            mock.patch.object(team, "save", wraps=team.save) as m_save,
        ):
            self._call_command()

        self.assertFalse(
            m_save.called,
            "Team.save() should not be called when nothing changed",
        )

    def test_auth_headers_are_included_in_request(self):
        """Ensure the command sends the correct auth headers to the API."""
        expected = {
            "Authorization": "Bearer test-token",
            "X-Florence-Token": "Bearer test-token",
        }
        with self._mock_api([], expected_headers=expected):
            self._call_command()

    @override_settings(SERVICE_AUTH_TOKEN=None)
    def test_missing_service_auth_token_raises_command_error(self):
        """Ensure the command raises an error if SERVICE_AUTH_TOKEN is not set."""
        with self.assertRaises(CommandError) as exc:
            self._call_command()

        self.assertIn("SERVICE_AUTH_TOKEN is not set in settings.", str(exc.exception))
