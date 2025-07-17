from django.conf import settings
from django.test import TestCase, override_settings

from cms.auth.checks import check_auth_settings, check_identity_api_settings


class AuthSettingsCheckTests(TestCase):
    """Tests for check_auth_settings which validates AWS Cognito and session configuration."""

    def test_cognito_disabled_no_errors(self):
        """When AWS_COGNITO_LOGIN_ENABLED is False, no Cognito settings are required."""
        with override_settings(AWS_COGNITO_LOGIN_ENABLED=False):
            errors = check_auth_settings(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_USER_POOL_ID=None,
        AWS_COGNITO_APP_CLIENT_ID=None,
        AWS_REGION=None,
        AUTH_TOKEN_REFRESH_URL=None,
        LOGOUT_REDIRECT_URL=None,
    )
    def test_missing_cognito_settings(self):
        """When AWS_COGNITO_LOGIN_ENABLED=True but required settings are missing,
        each missing setting should raise an Error with the appropriate id.
        """
        errors = check_auth_settings(app_configs=None)

        self.assertEqual(len(errors), 5)
        error_ids = [error.id for error in errors]
        self.assertIn("auth.E001", error_ids)  # Missing AWS_COGNITO_USER_POOL_ID
        self.assertIn("auth.E002", error_ids)  # Missing AWS_COGNITO_APP_CLIENT_ID
        self.assertIn("auth.E003", error_ids)  # Missing AWS_REGION
        self.assertIn("auth.E004", error_ids)  # Missing AUTH_TOKEN_REFRESH_URL
        self.assertIn("auth.E005", error_ids)  # Missing LOGOUT_REDIRECT_URL

    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_USER_POOL_ID="",
        AWS_COGNITO_APP_CLIENT_ID="",
        AWS_REGION="",
        AUTH_TOKEN_REFRESH_URL="",
        LOGOUT_REDIRECT_URL="",
    )
    def test_empty_cognito_settings(self):
        """When required Cognito settings are defined but empty, we should get errors."""
        errors = check_auth_settings(app_configs=None)

        self.assertEqual(len(errors), 5)

        # Check specific error messages and hints
        pool_id_error = next(e for e in errors if e.id == "auth.E001")
        self.assertIn("AWS_COGNITO_USER_POOL_ID is required", pool_id_error.msg)
        self.assertIn("eu-west-2_xxxxxxxxx", pool_id_error.hint)

        client_id_error = next(e for e in errors if e.id == "auth.E002")
        self.assertIn("AWS_COGNITO_APP_CLIENT_ID is required", client_id_error.msg)
        self.assertIn("the-cognito-app-client-id", client_id_error.hint)

    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_USER_POOL_ID="eu-west-2_test123",
        AWS_COGNITO_APP_CLIENT_ID="test-client-id",
        AWS_REGION="eu-west-2",
        AUTH_TOKEN_REFRESH_URL="http://localhost:29500/tokens/self",
        LOGOUT_REDIRECT_URL="http://localhost:29500/logout",
    )
    def test_all_cognito_settings_present(self):
        """When AWS_COGNITO_LOGIN_ENABLED=True and all required settings are defined,
        there should be no errors.
        """
        errors = check_auth_settings(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        SESSION_COOKIE_AGE=300,
        SESSION_RENEWAL_OFFSET_SECONDS=400,
    )
    def test_session_renewal_offset_too_large(self):
        """When SESSION_RENEWAL_OFFSET_SECONDS >= SESSION_COOKIE_AGE, we should get an error."""
        errors = check_auth_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "auth.E006")
        self.assertIn(
            f"SESSION_RENEWAL_OFFSET_SECONDS ({settings.SESSION_RENEWAL_OFFSET_SECONDS}) should be less than",
            error.msg,
        )
        self.assertIn(f"SESSION_COOKIE_AGE ({settings.SESSION_COOKIE_AGE})", error.msg)

    @override_settings(
        SESSION_COOKIE_AGE=600,
        SESSION_RENEWAL_OFFSET_SECONDS=300,
    )
    def test_session_renewal_offset_valid(self):
        """When SESSION_RENEWAL_OFFSET_SECONDS < SESSION_COOKIE_AGE, no error."""
        errors = check_auth_settings(app_configs=None)
        self.assertEqual(errors, [])

    def test_session_settings_not_defined(self):
        """When session settings are not defined, no errors should occur."""
        # Remove settings if they exist
        with override_settings():
            # This creates a clean settings without SESSION_COOKIE_AGE or SESSION_RENEWAL_OFFSET_SECONDS
            errors = check_auth_settings(app_configs=None)
            self.assertEqual(errors, [])


class IdentityAPISettingsCheckTests(TestCase):
    """Tests for check_identity_api_settings which validates identity API and team sync configuration."""

    @override_settings(
        IDENTITY_API_BASE_URL="https://identity.example.com",
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        SERVICE_AUTH_TOKEN=None,
    )
    def test_missing_service_auth_token(self):
        """When IDENTITY_API_BASE_URL is set and team sync is enabled but SERVICE_AUTH_TOKEN is missing,
        we should get an error.
        """
        errors = check_identity_api_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "auth.E009")
        self.assertIn("SERVICE_AUTH_TOKEN is required when AWS_COGNITO_TEAM_SYNC_ENABLED is True.", error.msg)

    @override_settings(
        IDENTITY_API_BASE_URL="https://identity.example.com",
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        SERVICE_AUTH_TOKEN="",
    )
    def test_empty_service_auth_token(self):
        """Empty SERVICE_AUTH_TOKEN should also trigger an error."""
        errors = check_identity_api_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "auth.E009")

    @override_settings(
        IDENTITY_API_BASE_URL="https://identity.example.com",
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        SERVICE_AUTH_TOKEN="valid-token",
    )
    def test_identity_api_with_valid_token(self):
        """When all identity API settings are properly configured, no errors."""
        errors = check_identity_api_settings(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        IDENTITY_API_BASE_URL=None,
        AWS_COGNITO_TEAM_SYNC_ENABLED=False,
        SERVICE_AUTH_TOKEN="valid-token",
    )
    def test_cognito_enabled_identity_api_url_missing(self):
        """When AWS_COGNITO_LOGIN_ENABLED is True and IDENTITY_API_BASE_URL is not set, should raise E007."""
        errors = check_identity_api_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "auth.E007")
        self.assertIn(
            (
                "IDENTITY_API_BASE_URL is required when AWS_COGNITO_LOGIN_ENABLED or "
                "AWS_COGNITO_TEAM_SYNC_ENABLED is True."
            ),
            error.msg,
        )

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        IDENTITY_API_BASE_URL=None,
        SERVICE_AUTH_TOKEN="valid-token",
    )
    def test_team_sync_enabled_identity_api_url_missing(self):
        """When AWS_COGNITO_TEAM_SYNC_ENABLED is True and IDENTITY_API_BASE_URL is not set, should raise E007."""
        errors = check_identity_api_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "auth.E007")
        self.assertIn(
            "IDENTITY_API_BASE_URL is required when AWS_COGNITO_LOGIN_ENABLED or AWS_COGNITO_TEAM_SYNC_ENABLED is True.",
            error.msg,
        )

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        IDENTITY_API_BASE_URL=None,
        SERVICE_AUTH_TOKEN=None,
    )
    def test_team_sync_enabled_missing_identity_api_url_and_service_auth_token(self):
        """When team sync is enabled but both IDENTITY_API_BASE_URL and SERVICE_AUTH_TOKEN are missing,
        should raise E007 and E009.
        """
        errors = check_identity_api_settings(app_configs=None)

        self.assertEqual(len(errors), 2)
        error_ids = {e.id for e in errors}
        self.assertIn("auth.E007", error_ids)
        self.assertIn("auth.E009", error_ids)

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=False,
    )
    def test_team_sync_disabled(self):
        """When team sync is disabled, SERVICE_AUTH_TOKEN and IDENTITY_API_BASE_URL is not required."""
        errors = check_identity_api_settings(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        IDENTITY_API_BASE_URL="https://identity.example.com",
        SERVICE_AUTH_TOKEN="valid-token",
        AWS_COGNITO_TEAM_SYNC_FREQUENCY=0,
    )
    def test_team_sync_frequency_zero(self):
        """When AWS_COGNITO_TEAM_SYNC_FREQUENCY is 0, we should get an error."""
        errors = check_identity_api_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "auth.E008")
        self.assertIn("AWS_COGNITO_TEAM_SYNC_FREQUENCY must be at least 1", error.msg)
        self.assertIn(f"(got {settings.AWS_COGNITO_TEAM_SYNC_FREQUENCY})", error.msg)

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        IDENTITY_API_BASE_URL="https://identity.example.com",
        SERVICE_AUTH_TOKEN="valid-token",
        AWS_COGNITO_TEAM_SYNC_FREQUENCY=-5,
    )
    def test_team_sync_frequency_negative(self):
        """When AWS_COGNITO_TEAM_SYNC_FREQUENCY is negative, we should get an error."""
        errors = check_identity_api_settings(app_configs=None)

        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error.id, "auth.E008")
        self.assertIn(f"(got {settings.AWS_COGNITO_TEAM_SYNC_FREQUENCY})", error.msg)

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        IDENTITY_API_BASE_URL="https://identity.example.com",
        SERVICE_AUTH_TOKEN="valid-token",
        AWS_COGNITO_TEAM_SYNC_FREQUENCY=1,
    )
    def test_team_sync_frequency_valid(self):
        """When AWS_COGNITO_TEAM_SYNC_FREQUENCY is valid (>= 1), no error."""
        errors = check_identity_api_settings(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        IDENTITY_API_BASE_URL="https://identity.example.com",
        SERVICE_AUTH_TOKEN="valid-token",
    )
    def test_team_sync_frequency_not_set(self):
        """When AWS_COGNITO_TEAM_SYNC_FREQUENCY is not set, no error (defaults are assumed valid)."""
        errors = check_identity_api_settings(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(
        AWS_COGNITO_TEAM_SYNC_ENABLED=False,
        AWS_COGNITO_TEAM_SYNC_FREQUENCY=0,
    )
    def test_team_sync_disabled_ignores_frequency(self):
        """When team sync is disabled, frequency validation is skipped."""
        errors = check_identity_api_settings(app_configs=None)
        self.assertEqual(errors, [])


class CombinedChecksTests(TestCase):
    """Tests for scenarios involving both auth and identity API checks."""

    @override_settings(
        AWS_COGNITO_LOGIN_ENABLED=True,
        AWS_COGNITO_USER_POOL_ID="eu-west-2_test",
        AWS_COGNITO_APP_CLIENT_ID="test-client",
        AWS_REGION="eu-west-2",
        AUTH_TOKEN_REFRESH_URL="http://localhost:29500/tokens/self",
        LOGOUT_REDIRECT_URL="http://localhost:29500/logout",
        SESSION_COOKIE_AGE=300,
        SESSION_RENEWAL_OFFSET_SECONDS=400,
        AWS_COGNITO_TEAM_SYNC_ENABLED=True,
        SERVICE_AUTH_TOKEN="valid-token",
        AWS_COGNITO_TEAM_SYNC_FREQUENCY=0,
    )
    def test_multiple_errors_across_checks(self):
        """Test that multiple errors can be detected across different check functions."""
        # Test auth settings
        auth_errors = check_auth_settings(app_configs=None)
        self.assertEqual(len(auth_errors), 1)  # Session renewal offset error
        self.assertEqual(auth_errors[0].id, "auth.E006")

        # Test identity API settings
        identity_errors = check_identity_api_settings(app_configs=None)
        self.assertEqual(len(identity_errors), 2)  # Missing token and invalid frequency
        error_ids = [e.id for e in identity_errors]
        self.assertIn("auth.E007", error_ids)
        self.assertIn("auth.E008", error_ids)
