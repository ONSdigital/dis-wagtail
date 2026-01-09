import uuid
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from cms.auth import wagtail_hooks
from cms.auth.middleware import JWT_SESSION_ID_KEY
from cms.auth.tests.helpers import CognitoTokenTestCase, build_jwt
from cms.users.models import User


class AuthIntegrationTests(CognitoTokenTestCase):
    def test_first_time_login_creates_user_and_session(self):
        # Happy-path: valid tokens, no prior session
        self.login_with_tokens()
        self.assertFalse(User.objects.filter(external_user_id=self.user_uuid).exists())
        self.assertLoggedIn()

        # Session key set
        self.assertIn(JWT_SESSION_ID_KEY, self.client.session)
        self.assertEqual(self.client.session[JWT_SESSION_ID_KEY], "jti-accessjti-id")

    def test_group_assignment_for_admin_and_officer_roles(self):
        """Check group assignment for users with admin and officer roles."""
        role_group_map = {
            "role-admin": settings.PUBLISHING_ADMINS_GROUP_NAME,
            "role-publisher": settings.PUBLISHING_OFFICERS_GROUP_NAME,
        }
        for role, expected_group in role_group_map.items():
            with self.subTest(role=role):
                self.login_with_tokens(groups=[role])

                # Ensure user does not exist before login
                User.objects.filter(external_user_id=self.user_uuid).delete()
                self.assertLoggedIn()

                # User should be in the expected group
                self.assertInGroups(expected_group, settings.VIEWERS_GROUP_NAME)

    def test_group_assignment_for_multiple_roles(self):
        """Check group assignment when user has both admin and officer roles."""
        groups = ["role-admin", "role-publisher"]
        self.login_with_tokens(groups=groups)

        User.objects.filter(external_user_id=self.user_uuid).delete()
        self.assertLoggedIn()

        # User should be in both admin and officer groups
        self.assertInGroups(
            settings.PUBLISHING_ADMINS_GROUP_NAME,
            settings.PUBLISHING_OFFICERS_GROUP_NAME,
            settings.VIEWERS_GROUP_NAME,
        )

    def test_existing_user_details_are_updated_on_login(self):
        """User details are updated if Cognito tokens provide new info."""
        # Create a user with old details and external_user_id
        user = User.objects.create(
            username="testuser",
            email="old_email@example.com",
            first_name="OldFirst",
            last_name="OldLast",
            external_user_id=self.user_uuid,
        )

        # Generate tokens with updated details
        new_email = "new_email@example.com"
        new_first = "NewFirst"
        new_last = "NewLast"

        access = build_jwt(
            self.keypair,
            token_use="access",
            username=self.user_uuid,
            client_id=settings.AWS_COGNITO_APP_CLIENT_ID,
        )
        id_token = build_jwt(
            self.keypair,
            token_use="id",
            aud=settings.AWS_COGNITO_APP_CLIENT_ID,
            **{
                "cognito:username": self.user_uuid,
                "email": new_email,
                "given_name": new_first,
                "family_name": new_last,
            },
        )

        self.set_jwt_cookies(access, id_token)
        # Trigger authentication (middleware runs)
        self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        # Refresh from DB and check details updated
        user.refresh_from_db()
        self.assertEqual(user.email, new_email)
        self.assertEqual(user.first_name, new_first)
        self.assertEqual(user.last_name, new_last)

    def test_subsequent_request_uses_existing_session_when_jti_unchanged(self):
        self.login_with_tokens()
        self.assertLoggedIn()
        first_key = self.client.session[JWT_SESSION_ID_KEY]

        # Simulate a subsequent request with the same tokens
        self.assertLoggedIn()
        subsequent_key = self.client.session[JWT_SESSION_ID_KEY]
        self.assertEqual(subsequent_key, first_key)

    def test_missing_tokens_logs_out(self):
        """Subtest: missing both, only access, only id token -> logout external user."""
        user = User.objects.create(username="test", email="test@example.com")
        user.external_user_id = self.user_uuid
        user.set_unusable_password()
        user.save()

        scenarios = [
            {
                "name": "missing_both",
                "set_access": False,
                "set_id": False,
                "desc": "No JWT cookies + external user in session -> immediate logout.",
            },
            {
                "name": "missing_id",
                "set_access": True,
                "set_id": False,
                "desc": "Only access token -> logout external user.",
            },
            {
                "name": "missing_access",
                "set_access": False,
                "set_id": True,
                "desc": "Only ID token -> logout external user.",
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                self.client.force_login(user)
                # Clear cookies
                self.client.cookies.pop(settings.ACCESS_TOKEN_COOKIE_NAME, None)
                self.client.cookies.pop(settings.ID_TOKEN_COOKIE_NAME, None)
                # Set cookies as needed
                if scenario["set_access"]:
                    access, _ = self.generate_tokens()
                    self.client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = access
                if scenario["set_id"]:
                    _, id_token = self.generate_tokens()
                    self.client.cookies[settings.ID_TOKEN_COOKIE_NAME] = id_token

                self.assertLoggedOut()

    def test_expired_or_invalid_jwt_logs_out(self):
        """Subtest: expired access, expired id, both expired -> logout external user."""
        scenarios = [
            {
                "name": "expired_access",
                "access_exp": 0,
                "id_exp": None,
                "desc": "Expired access token, valid id token",
            },
            {
                "name": "expired_id",
                "access_exp": None,
                "id_exp": 0,
                "desc": "Valid access token, expired id token",
            },
            {
                "name": "both_expired",
                "access_exp": 0,
                "id_exp": 0,
                "desc": "Both tokens expired",
            },
        ]
        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                access = build_jwt(
                    self.keypair,
                    token_use="access",
                    username=self.user_uuid,
                    client_id=settings.AWS_COGNITO_APP_CLIENT_ID,
                    exp=scenario["access_exp"] if scenario["access_exp"] is not None else None,
                )
                id_token = build_jwt(
                    self.keypair,
                    token_use="id",
                    aud=settings.AWS_COGNITO_APP_CLIENT_ID,
                    **{
                        "cognito:username": self.user_uuid,
                        "email": f"{self.user_uuid}@example.com",
                        "exp": scenario["id_exp"] if scenario["id_exp"] is not None else None,
                    },
                )
                self.set_jwt_cookies(access, id_token)
                self.assertLoggedOut()

    def test_client_id_mismatch_logs_out(self):
        self.login_with_tokens(client_id="wrong")
        self.assertLoggedOut()

    def test_username_mismatch_between_tokens(self):
        uuid_other = str(uuid.uuid4())
        # Log in with valid tokens for user_uuid
        self.login_with_tokens()
        self.assertLoggedIn()

        access = build_jwt(
            self.keypair,
            token_use="access",
            username=self.user_uuid,
            client_id=settings.AWS_COGNITO_APP_CLIENT_ID,
        )

        id_token = build_jwt(
            self.keypair,
            token_use="id",
            aud=settings.AWS_COGNITO_APP_CLIENT_ID,
            **{"cognito:username": uuid_other, "email": "test@example.com"},
        )

        self.set_jwt_cookies(access, id_token)
        self.assertLoggedOut()

    def test_token_mismatch_session(self):
        uuid_other = str(uuid.uuid4())
        # Log in with valid tokens for user_uuid
        self.login_with_tokens()
        self.assertFalse(User.objects.filter(external_user_id=self.user_uuid).exists())

        self.assertLoggedIn()

        # Now swap to tokens for a different user
        access_2, id_token_2 = self.generate_tokens(username=uuid_other)
        self.set_jwt_cookies(access_2, id_token_2)

        response_2 = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertEqual(response_2.status_code, 302)
        self.assertFalse(response_2.wsgi_request.user.is_authenticated)
        # User shouldn't exist after login
        self.assertFalse(User.objects.filter(external_user_id=uuid_other).exists())

    def test_session_update_on_new_jti(self):
        # First login with default JTIs
        self.login_with_tokens()
        self.assertLoggedIn()

        old_key = self.client.session[JWT_SESSION_ID_KEY]

        #  Now mint a pair of tokens by overriding jti
        access_2 = build_jwt(
            self.keypair,
            token_use="access",
            username=self.user_uuid,
            client_id=settings.AWS_COGNITO_APP_CLIENT_ID,
            jti="jti-access-2",  # override
        )

        id_token_2 = build_jwt(
            self.keypair,
            token_use="id",
            aud=settings.AWS_COGNITO_APP_CLIENT_ID,
            **{
                "cognito:username": self.user_uuid,
                "email": f"{self.user_uuid}@example.com",
                "jti": "jti-id-2",  # override
            },
        )
        self.set_jwt_cookies(access_2, id_token_2)

        self.assertLoggedIn()
        new_key = self.client.session[JWT_SESSION_ID_KEY]

        # Now they differ
        self.assertNotEqual(new_key, old_key)
        self.assertEqual(new_key, "jti-access-2jti-id-2")

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_external_user_with_jwt_not_authenticated_when_cognito_disabled(self):
        """External user with valid JWTs is NOT authenticated when Cognito is disabled."""
        self.login_with_tokens()
        self.assertLoggedOut()

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_core_admin_login_available_when_cognito_disabled(self):
        User.objects.create_superuser(username="test", email="test@example.com", password="password123")
        response = self.client.post(
            "/admin/login/",
            {
                "username": "test",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect on successful login
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # User with username 'test' should now exist after login
        self.assertTrue(User.objects.filter(username="test").exists())

    def test_core_admin_login_available_when_cognito_enabled(self):
        User.objects.create_superuser(username="test", email="test@example.com", password="password123")
        response = self.client.post(
            "/admin/login/",
            {
                "username": "test",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirect on successful login
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # User with username 'test' should now exist after login
        self.assertTrue(User.objects.filter(username="test").exists())

    def test_core_admin_disabled_logs_out(self):
        """Test that when WAGTAIL_CORE_ADMIN_LOGIN_ENABLED is set to False,
        an authenticated user is logged out upon accessing the Wagtail admin home path.
        """
        # Create and login as superuser
        User.objects.create_superuser(username="test", email="test@example.com", password="password123")
        response = self.client.post(
            "/admin/login/",
            {
                "username": "test",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # User with username 'test' should now exist after login
        self.assertTrue(User.objects.filter(username="test").exists())

        # Now flip the flag to False and access the admin home
        with override_settings(WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False):
            response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
            self.assertLoggedOut()

    @override_settings(WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False)
    def test_core_admin_unavailable_when_core_admin_disabled(self):
        """Test that the core admin login page is unavailable when WAGTAIL_CORE_ADMIN_LOGIN_ENABLED is False."""
        User.objects.create_superuser(username="test", email="test@example.com", password="password123")
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        # Should redirect to florence login page or similar
        self.assertEqual(response.status_code, 302)

    def test_logout_view_clears_cookies(self):
        self.login_with_tokens()
        self.assertLoggedIn()

        response = self.client.post(reverse("wagtailadmin_logout"))

        # The cookies should still be present in response.cookies, but their value should be empty
        for name in (settings.ACCESS_TOKEN_COOKIE_NAME, settings.ID_TOKEN_COOKIE_NAME):
            self.assertIn(name, response.cookies, f"{name} should be in response.cookies (deleted via empty value)")
            morsel = response.cookies[name]
            # Empty string value means deleted
            self.assertEqual(morsel.value, "")
            # And max-age=0 confirms deletion
            self.assertIn(morsel.get("max-age"), ("0", 0))

        self.assertLoggedOut()

    def test_extend_session_post_and_get(self):
        # Mint tokens and set cookies
        self.login_with_tokens()
        self.assertLoggedIn()

        # POST to extend_session
        url = reverse("extend_session")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "success", "message": "Session extended."})

        # The session expiry should be updated after POST
        session_expiry_before = self.client.session.get_expiry_date()

        # POST to extend_session again to update expiry
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        session_expiry_after = self.client.session.get_expiry_date()

        self.assertGreater(session_expiry_after, session_expiry_before)

        # GET should return 405
        response_2 = self.client.get(url)
        self.assertEqual(response_2.status_code, 405)
        self.assertJSONEqual(response_2.content, {"status": "error", "message": "Invalid request method."})


class WagtailHookTests(CognitoTokenTestCase):
    def test_wagtail_hook_injection(self):
        with patch.object(wagtail_hooks, "static", lambda path: f"/static/{path}"):
            # set cookies and hit /admin/
            self.login_with_tokens()
            self.assertLoggedIn()

            resp = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode()

            self.assertIn('<script id="auth-config"', html)
            self.assertIn('"wagtailAdminHomePath":', html)
            self.assertIn('<script src="/static/js/auth.js"', html)

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_wagtail_hook_not_registered(self):
        # Create and login as superuser
        User.objects.create_superuser(username="test", email="test@example.com", password="password123")
        response = self.client.post(
            "/admin/login/",
            {
                "username": "test",
                "password": "password123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # User with username 'test' should now exist after login
        self.assertTrue(User.objects.filter(username="test").exists())

        response_admin = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        html = response_admin.content.decode()

        self.assertNotIn('id="auth-config"', html)
        self.assertNotIn("auth.js", html)
