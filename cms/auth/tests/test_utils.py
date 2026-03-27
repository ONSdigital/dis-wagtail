import base64
import importlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest import mock

import jwt
import requests
from django.conf import settings
from django.core.cache import caches
from django.test import SimpleTestCase, override_settings

from cms.auth import utils
from cms.auth.tests.helpers import DummyResponse, build_jwt, generate_rsa_keypair


class ValidateJWTTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.good_pair = generate_rsa_keypair()
        cls.bad_pair = generate_rsa_keypair()

    def _patch_jwks(self, pair=None):
        """Patch utils.get_jwks() so only pair's public key is returned."""
        pair = pair or self.good_pair
        b64_der = base64.b64encode(pair.public_der).decode()

        return mock.patch("cms.auth.utils.get_jwks", return_value={pair.kid: b64_der})

    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
        AWS_REGION="eu-west-2",
    )
    def test_id_token_happy_path(self):
        importlib.reload(utils)
        uid = str(uuid.uuid4())
        token = build_jwt(
            self.good_pair,
            token_use="id",
            **{
                "aud": "expected",
                "cognito:username": uid,
                "email": "x@y.com",
                "sub": uid,
            },
        )
        with self._patch_jwks():
            claims = utils.validate_jwt(token, token_type="id")

        self.assertIsNotNone(claims)
        self.assertEqual(claims["aud"], "expected")
        self.assertEqual(claims["token_use"], "id")

    def test_audience_mismatch_returns_none(self):
        token = build_jwt(
            self.good_pair,
            token_use="id",
            **{
                "aud": "wrong",
                "cognito:username": "u1",
                "email": "x@y.com",
            },
        )
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(token, token_type="id"))

    def test_invalid_signature_returns_none(self):
        # sign with bad key but JWKS only has good key
        bad_token = build_jwt(
            self.bad_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )
        with self._patch_jwks(pair=self.good_pair):  # wrong key in JWKS
            self.assertIsNone(utils.validate_jwt(bad_token, token_type="access"))

    def test_wrong_token_use_claim_returns_none(self):
        # access token but claim says id
        token = build_jwt(
            self.good_pair,
            token_use="id",  # incorrect for access validation
            **{
                "aud": "expected",
                "cognito:username": "u1",
                "email": "x@y.com",
            },
        )
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(token, token_type="access"))

    def test_missing_kid_in_jwks_returns_none(self):
        token = build_jwt(
            self.good_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )
        # JWKS dict is empty
        with mock.patch("cms.auth.utils.get_jwks", return_value={}):
            self.assertIsNone(utils.validate_jwt(token, token_type="access"))

    def test_get_jwks_uses_configured_timeout(self):
        # Reset any cached JWKS before running the test.
        caches["memory"].clear()
        # Re-import to ensure decorator cache is reset after other tests.
        importlib.reload(utils)

        token = build_jwt(
            self.good_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )
        with mock.patch("cms.auth.utils.requests.get") as mock_get:
            utils.validate_jwt(token, token_type="access")
            mock_get.assert_called_once()
            _, kwargs = mock_get.call_args
            self.assertEqual(kwargs["timeout"], settings.HTTP_REQUEST_DEFAULT_TIMEOUT_SECONDS)

    def test_jwks_fetch_network_error_returns_none(self):
        token = build_jwt(
            self.good_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )
        with mock.patch("cms.auth.utils.get_jwks", side_effect=requests.ConnectionError):
            self.assertIsNone(utils.validate_jwt(token, token_type="access"))

    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
        AWS_REGION="eu-west-2",
    )
    def test_valid_access_token(self):
        importlib.reload(utils)
        token = build_jwt(
            self.good_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )
        with self._patch_jwks():
            claims = utils.validate_jwt(token, token_type="access")

        self.assertIsNotNone(claims)
        self.assertEqual(claims["username"], "u1")

    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
    )
    def test_header_missing_kid_returns_none(self):
        bad_token = jwt.encode({"token_use": "access"}, "s" * 32, algorithm="HS256")
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(bad_token, token_type="access"))

    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
    )
    def test_expired_token(self):
        now = datetime.now(tz=UTC) - timedelta(hours=1)
        expired = jwt.encode(
            {
                "exp": int(now.timestamp()),
                "iat": int(now.timestamp()),
                "iss": "https://cognito-idp.eu-west-2.amazonaws.com/test-pool",
                "jti": "jti",
                "token_use": "access",
                "username": "x",
                "client_id": "expected",
            },
            self.good_pair.private,
            algorithm="RS256",
            headers={"kid": self.good_pair.kid},
        )
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(expired, token_type="access"))

    # Issuer mismatch -> validate_jwt() must return None
    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
    )
    def test_issuer_mismatch_returns_none(self):
        importlib.reload(utils)
        bad_iss = "https://evil.example.com/123"  # wrong issuer
        token = build_jwt(
            self.good_pair,
            token_use="id",
            iss=bad_iss,
            aud="expected",
            **{
                "cognito:username": "u1",
                "email": "x@y.com",
                "sub": "u1",
            },
        )
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(token, token_type="id"))

    # Wrong algorithm (HS256) -> returns None
    def test_wrong_algorithm_returns_none(self):
        # Use HS256, but still include a kid so header passes first check
        token = jwt.encode(
            {
                "token_use": "access",
                "username": "u1",
                "client_id": "expected",
                "sub": "u1",
            },
            "s" * 32,
            algorithm="HS256",
            headers={"kid": self.good_pair.kid},
        )

        # JWKS contains an RSA key so alg mismatch
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(token, token_type="access"))

    # Missing required claim username ->  returns None
    def test_missing_required_claim_returns_none(self):
        token = build_jwt(
            self.good_pair,
            token_use="access",
            # username intentionally omitted
            client_id="expected",
            sub="u1",
        )
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(token, token_type="access"))

    # Bearer -prefixed token string still validates
    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
        AWS_REGION="eu-west-2",
    )
    def test_bearer_prefix_trimming_succeeds(self):
        importlib.reload(utils)
        token = build_jwt(
            self.good_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )
        with self._patch_jwks():
            claims = utils.validate_jwt(f"Bearer {token}", token_type="access")
        self.assertIsNotNone(claims)
        self.assertEqual(claims["username"], "u1")

    # JWKS JSON decode error -> returns None
    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
    )
    def test_jwks_json_decode_error_returns_none(self):
        importlib.reload(utils)
        token = build_jwt(
            self.good_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )

        json_error = json.JSONDecodeError("Expecting value", doc="", pos=0)
        with mock.patch("cms.auth.utils.get_jwks", side_effect=json_error):
            self.assertIsNone(utils.validate_jwt(token, token_type="access"))

    # Generic exception inside utils._parse_der_public_key -> returns None
    def test_generic_exception_returns_none(self):
        token = build_jwt(
            self.good_pair,
            token_use="access",
            username="u1",
            client_id="expected",
            sub="u1",
        )

        with (
            self._patch_jwks(),  # JWKS is fine
            mock.patch("cms.auth.utils._parse_der_public_key", side_effect=ValueError("boom")),
        ):
            self.assertIsNone(utils.validate_jwt(token, token_type="access"))


@override_settings(
    AUTH_TOKEN_REFRESH_URL="/refresh/",
    WAGTAILADMIN_HOME_PATH="/admin/",
    CSRF_COOKIE_NAME="csrftoken",
    CSRF_HEADER_NAME="HTTP_X_CSRFTOKEN",
    SESSION_RENEWAL_OFFSET_SECONDS=30,
    ID_TOKEN_COOKIE_NAME="id",
)
class GetAuthConfigTests(SimpleTestCase):
    def test_json_config_contains_expected_keys(self):
        data = utils.get_auth_config()
        expected_keys = {
            "authTokenRefreshUrl",
            "wagtailAdminHomePath",
            "csrfCookieName",
            "csrfHeaderName",
            "sessionRenewalOffsetSeconds",
            "idTokenCookieName",
        }
        self.assertEqual(expected_keys, set(data.keys()))

    def test_values_exact(self):
        data = utils.get_auth_config()
        self.assertEqual(data["authTokenRefreshUrl"], "/refresh/")
        self.assertEqual(data["wagtailAdminHomePath"], "/admin/")
        self.assertEqual(data["csrfCookieName"], "csrftoken")
        self.assertEqual(data["csrfHeaderName"], "X-CSRFTOKEN")  # header rewritten
        self.assertEqual(data["sessionRenewalOffsetSeconds"], 30)
        self.assertEqual(data["idTokenCookieName"], "id")


class JWKSCacheTests(SimpleTestCase):
    def test_jwks_cached(self):
        response = DummyResponse({"foo": "bar"})
        with mock.patch("cms.auth.utils.requests.get", return_value=response) as mock_get:
            # Re-import under the test settings to clear the cache entirely
            importlib.reload(utils)

            utils.get_jwks()
            utils.get_jwks()
            self.assertEqual(mock_get.call_count, 1)  # cached second time
