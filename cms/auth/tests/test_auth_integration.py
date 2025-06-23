import base64
import importlib
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from cms.auth.tests.helpers import DummyResponse, build_jwt, generate_rsa_keypair

# from cms.auth.utils import JWKS_URL
from cms.auth import utils
from cms.auth.utils import validate_jwt
import uuid

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
        # Create test client and RSA keypair for JWTs
        self.client = Client()
        self.user_uuid = str(uuid.uuid4())
        self.keypair = generate_rsa_keypair()
        # Prepare JWKS stub (kid -> base64 DER public key)
        public_b64 = base64.b64encode(self.keypair.public_der).decode()
        self.jwks = {self.keypair.kid: public_b64}

        # # Monkey-patch requests.get to return our JWKS
        # requests.get = (
        #     lambda url, timeout=5: DummyResponse(self.jwks) if url == JWKS_URL else DummyResponse({}, status=404)
        # )

        importlib.reload(utils)

        utils.get_jwks = lambda: self.jwks

    def _set_jwt_cookies(self, access_token, id_token):
        self.client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = access_token
        self.client.cookies[settings.ID_TOKEN_COOKIE_NAME] = id_token

    def _generate_tokens(self, username=None, groups=None, client_id=None):
        username = username or self.user_uuid
        client_id = client_id or settings.AWS_COGNITO_APP_CLIENT_ID
        # Build access token

        access = build_jwt(
            self.keypair,
            token_use="access",
            username=username,
            client_id=client_id,
        )

        # Build ID token
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

    def test_jwt_validation_smoke(self):
        # breakpoint()
        access, id_token = self._generate_tokens()
        # strip “Bearer ” logic if needed
        access_payload = validate_jwt(access, token_type="access")
        id_payload = validate_jwt(id_token, token_type="id")
        assert access_payload is not None, "Access token failed to validate"
        assert id_payload is not None, "ID token failed to validate"

    def test_first_time_login_creates_user_and_session(self):
        # Happy-path: valid tokens, no prior session
        access, id_token = self._generate_tokens(groups=["Publishing Admins"])
        self._set_jwt_cookies(access, id_token)
        # breakpoint()
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        # breakpoint()
        # User should now exist and be authenticated

        user = User.objects.get(external_user_id=self.user_uuid)
        breakpoint()
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # Session key should be set to concatenated JTIs
        self.assertIn(JWT_SESSION_ID_KEY, self.client.session)
        self.assertEqual(self.client.session[JWT_SESSION_ID_KEY], "jti-accessjti-id")
        # # User details updated
        # self.assertEqual(user.email, "user1@example.com")
        # self.assertEqual(user.first_name, "First")
        # self.assertEqual(user.last_name, "Last")
        # # Group assignment
        # self.assertTrue(Group.objects.filter(name="Publishing Admins", user=user).exists())
