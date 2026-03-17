from django.test import SimpleTestCase, override_settings

from cms.teams.checks import check_florence_groups_url


class FlorenceGroupsUrlCheckTests(SimpleTestCase):
    @override_settings(ALLOW_TEAM_MANAGEMENT=True, AWS_COGNITO_TEAM_SYNC_ENABLED=True)
    def test_no_error_when_team_management_enabled(self):
        errors = check_florence_groups_url(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(ALLOW_TEAM_MANAGEMENT=False, AWS_COGNITO_TEAM_SYNC_ENABLED=False)
    def test_no_error_when_team_sync_disabled(self):
        errors = check_florence_groups_url(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        ALLOW_TEAM_MANAGEMENT=False,
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        FLORENCE_GROUPS_URL="",
    )
    def test_error_when_url_missing(self):
        errors = check_florence_groups_url(app_configs=None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "teams.E001")

    @override_settings(
        ALLOW_TEAM_MANAGEMENT=False,
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        FLORENCE_GROUPS_URL="https://florence.example.com/groups",
    )
    def test_no_error_when_url_configured(self):
        errors = check_florence_groups_url(app_configs=None)
        self.assertEqual(errors, [])
