import base64
import importlib
import uuid
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from wagtail import hooks

from cms.auth import utils as auth_utils
from cms.auth import wagtail_hooks
from cms.auth.tests.helpers import build_jwt, generate_rsa_keypair
from cms.auth.utils import validate_jwt

User = get_user_model()
JWT_SESSION_ID_KEY = "jwt_session_id"


@override_settings(
    AWS_COGNITO_LOGIN_ENABLED=True,
    AWS_COGNITO_APP_CLIENT_ID="test-client-id",
    AWS_REGION="eu-west-2",
    AWS_COGNITO_USER_POOL_ID="test-pool",
    IDENTITY_API_BASE_URL="https://cognito-idp.eu-west-2.amazonaws.com/test-pool",
    ACCESS_TOKEN_COOKIE_NAME="access",
    ID_TOKEN_COOKIE_NAME="id",
    WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True,
    AUTH_TOKEN_REFRESH_URL="/auth/refresh/",
    WAGTAILADMIN_HOME_PATH="/admin/",
    CSRF_COOKIE_NAME="csrftoken",
    SESSION_RENEWAL_OFFSET_SECONDS=300,
)
class AuthIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_uuid = str(uuid.uuid4())

        # RSA keypair and JWKS stub
        self.keypair = generate_rsa_keypair()
        public_b64 = base64.b64encode(self.keypair.public_der).decode()
        self.jwks = {self.keypair.kid: public_b64}

        # Reload utils so module constants use overridden settings
        importlib.reload(auth_utils)
        # Stub JWKS fetch
        auth_utils.get_jwks = lambda: self.jwks

    def _generate_tokens(self, username=None, groups=None, client_id=None):
        username = username or self.user_uuid
        client_id = client_id or settings.AWS_COGNITO_APP_CLIENT_ID
        access = build_jwt(
            self.keypair,
            token_use="access",
            username=username,
            client_id=client_id,
        )
        id_payload = {
            "cognito:username": username,
            "email": f"{username}@example.com",
            "given_name": "First",
            "family_name": "Last",
        }
        if groups is not None:
            id_payload["cognito:groups"] = groups
        id_token = build_jwt(self.keypair, token_use="id", aud=client_id, **id_payload)
        return access, id_token

    def _set_jwt_cookies(self, access_token, id_token):
        self.client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = access_token
        self.client.cookies[settings.ID_TOKEN_COOKIE_NAME] = id_token

    def test_jwt_validation_smoke(self):
        access, id_token = self._generate_tokens()
        access_payload = validate_jwt(access, token_type="access")
        id_payload = validate_jwt(id_token, token_type="id")
        self.assertIsNotNone(access_payload, "Access token failed to validate")
        self.assertIsNotNone(id_payload, "ID token failed to validate")

    def test_first_time_login_creates_user_and_session(self):
        # Happy-path: valid tokens, no prior session
        access, id_token = self._generate_tokens(groups=["role-admin"])
        self._set_jwt_cookies(access, id_token)

        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        user = User.objects.get(external_user_id=self.user_uuid)
        # user is now authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        # Session key set
        self.assertIn(JWT_SESSION_ID_KEY, self.client.session)
        self.assertEqual(self.client.session[JWT_SESSION_ID_KEY], "jti-accessjti-id")

        # Group assignment:
        self.assertTrue(
            Group.objects.filter(name=settings.PUBLISHING_ADMIN_GROUP_NAME, user=user).exists(),
            "User should have been added to the Publishing Admin group",
        )
        # Always in the Viewer group
        self.assertTrue(
            Group.objects.filter(name=settings.VIEWERS_GROUP_NAME, user=user).exists(),
            "User should always be in the Viewer group",
        )

    def test_second_request_uses_existing_session(self):
        access, id_token = self._generate_tokens()
        self._set_jwt_cookies(access, id_token)
        self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        initial_key = self.client.session[JWT_SESSION_ID_KEY]

        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertEqual(self.client.session[JWT_SESSION_ID_KEY], initial_key)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_missing_both_tokens_logs_out(self):
        """No JWT cookies + external user in session -> immediate logout."""
        # Create an external user (unusable password + external_user_id)
        user = User.objects.create(username="test", email="test@example.com")
        user.external_user_id = self.user_uuid
        user.set_unusable_password()
        user.save()

        # Log them in (session cookie set)
        self.client.force_login(user)
        # Ensure no JWT cookies
        self.client.cookies.pop(settings.ACCESS_TOKEN_COOKIE_NAME, None)
        self.client.cookies.pop(settings.ID_TOKEN_COOKIE_NAME, None)

        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        # They should be kicked back to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_missing_only_access_token_logs_out(self):
        """Only access token -> logout external user."""
        user = User.objects.create(username="test", email="test@example.com")
        user.external_user_id = self.user_uuid
        user.set_unusable_password()
        user.save()

        self.client.force_login(user)
        access, _ = self._generate_tokens(groups=["role-admin"])

        # Set only access cookie
        self.client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = access
        self.client.cookies.pop(settings.ID_TOKEN_COOKIE_NAME, None)

        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_missing_only_id_token_logs_out(self):
        """Only ID token -> logout external user."""
        user = User.objects.create(username="test", email="test@example.com")
        user.external_user_id = self.user_uuid
        user.set_unusable_password()
        user.save()

        self.client.force_login(user)
        _, id_token = self._generate_tokens(groups=["role-admin"])

        # Set only ID cookie
        self.client.cookies.pop(settings.ACCESS_TOKEN_COOKIE_NAME, None)
        self.client.cookies[settings.ID_TOKEN_COOKIE_NAME] = id_token

        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_expired_or_invalid_jwt_logs_out(self):
        expired = build_jwt(
            self.keypair,
            token_use="access",
            username=self.user_uuid,
            client_id=settings.AWS_COGNITO_APP_CLIENT_ID,
            exp=0,
        )
        _, id_token = self._generate_tokens()
        self._set_jwt_cookies(expired, id_token)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_client_id_mismatch_logs_out(self):
        access, id_token = self._generate_tokens(client_id="wrong")
        self._set_jwt_cookies(access, id_token)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_username_mismatch_between_tokens(self):
        uuid_id_token = str(uuid.uuid4())

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
            **{"cognito:username": uuid_id_token, "email": "test@example.com"},
        )

        self._set_jwt_cookies(access, id_token)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_token_swap_attack_prevention(self):
        user_a = User.objects.create_user(username="test", email="test@example.com")
        user_a.external_user_id = self.user_uuid
        self.client.force_login(user_a)

        access, id_token = self._generate_tokens(username="test_2")
        self._set_jwt_cookies(access, id_token)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_session_update_on_new_jti(self):
        # First login with default JTIs
        access_1, id_token_1 = self._generate_tokens(groups=["role-admin"])
        self._set_jwt_cookies(access_1, id_token_1)
        self.client.get(settings.WAGTAILADMIN_HOME_PATH)
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
                "given_name": "First",
                "family_name": "Last",
                "cognito:groups": ["role-admin"],
                "jti": "jti-id-2",  # override
            },
        )
        self._set_jwt_cookies(access_2, id_token_2)

        self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        new_key = self.client.session[JWT_SESSION_ID_KEY]

        # Now they differ
        self.assertNotEqual(new_key, old_key)
        self.assertEqual(new_key, "jti-access-2jti-id-2")

    def test_external_user_with_jwt_authenticated_when_cognito_enabled(self):
        """External user with valid JWTs is authenticated when Cognito is enabled."""
        access, id_token = self._generate_tokens(groups=["role-admin"])
        self._set_jwt_cookies(access, id_token)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertTrue(response.wsgi_request.user.is_authenticated)

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_external_user_with_jwt_not_authenticated_when_cognito_disabled(self):
        """External user with valid JWTs is NOT authenticated when Cognito is disabled."""
        access, id_token = self._generate_tokens(groups=["role-admin"])
        self._set_jwt_cookies(access, id_token)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_cognito_disabled_keeps_local(self):
        user = User.objects.create_user(username="test", email="test@example.com")
        self.client.force_login(user)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertTrue(response.wsgi_request.user.is_authenticated)

    @override_settings(WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=False)
    def test_core_admin_disabled_logs_out(self):
        user = User.objects.create_user(username="test", email="test@example.com")
        self.client.force_login(user)
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_view_clears_cookies(self):
        access, id_token = self._generate_tokens()
        self._set_jwt_cookies(access, id_token)
        response = self.client.post(reverse("wagtailadmin_logout"))

        # The cookies should still be present in response.cookies, but their value should be empty
        for name in (settings.ACCESS_TOKEN_COOKIE_NAME, settings.ID_TOKEN_COOKIE_NAME):
            self.assertIn(name, response.cookies, f"{name} should be in response.cookies (deleted via empty value)")
            morsel = response.cookies[name]
            # Empty string value means deleted
            self.assertEqual(morsel.value, "")
            # And max-age=0 confirms deletion
            self.assertIn(morsel.get("max-age"), ("0", 0))

    def test_extend_session_post_and_get(self):
        # Mint tokens and set cookies
        access, id_token = self._generate_tokens(groups=["role-admin"])
        self._set_jwt_cookies(access, id_token)

        # POST to extend_session
        url = reverse("extend_session")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "success", "message": "Session extended."})

        # GET should return 405
        response_2 = self.client.get(url)
        self.assertEqual(response_2.status_code, 405)
        self.assertJSONEqual(response_2.content, {"status": "error", "message": "Invalid request method."})


class WagtailHookTests(TestCase):
    def setUp(self):
        # Always clear out any leftover hook registrations
        hooks._hooks.pop("insert_global_admin_js", None)  # pylint: disable=protected-access

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=True)
    def test_wagtail_hook_injection(self):
        # Reload so the decorator runs under AWS_COGNITO_LOGIN_ENABLED=True
        importlib.reload(wagtail_hooks)

        #  Monkey-patch the static function *in that module:
        with patch.object(wagtail_hooks, "static", lambda path: f"/static/{path}"):
            hook_funcs = hooks.get_hooks("insert_global_admin_js")
            self.assertEqual(len(hook_funcs), 1)

            rendered = hook_funcs[0]()  # now calls our patched static
            self.assertIn('<script id="auth-config"', rendered)
            self.assertIn('"wagtailAdminHomePath":', rendered)
            self.assertIn('<script src="/static/js/auth.js"', rendered)

    @override_settings(AWS_COGNITO_LOGIN_ENABLED=False)
    def test_wagtail_hook_not_registered(self):
        importlib.reload(wagtail_hooks)

        hooks_list = hooks.get_hooks("insert_global_admin_js")
        self.assertEqual(len(hooks_list), 0)
