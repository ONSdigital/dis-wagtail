# tests/test_utils.py
import base64
import importlib
import json
from datetime import UTC, datetime, timedelta
from unittest import mock

import jwt
from django.test import SimpleTestCase, override_settings

from cms.auth import utils  # pylint: disable=import-error
from cms.auth.tests.helpers import DummyResponse, build_jwt, generate_rsa_keypair


class ValidateJWTTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pair = generate_rsa_keypair()

    def _patch_jwks(self):
        """Return a context-manager that patches cms.auth.utils.get_jwks()
        to hand back a dict of {kid: base64-encoded DER}.

        Patched here instead of requests.get() so we don't worry about the
        internal memory_cache or the request URL.
        """
        b64_der = base64.b64encode(self.pair.public_der).decode()

        # clear the memoised cache so each test gets a fresh value
        try:
            utils.get_jwks.cache_clear()  # functools.lru_cache
        except AttributeError:
            utils.get_jwks.invalidate()  # if you are using django-cache-utils

        return mock.patch("cms.auth.utils.get_jwks", return_value={self.pair.kid: b64_der})

    @override_settings(
        AWS_COGNITO_USER_POOL_ID="test-pool",
        AWS_COGNITO_APP_CLIENT_ID="expected",
    )
    def test_valid_access_token(self):
        importlib.reload(utils)
        token = build_jwt(
            self.pair,
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
        bad_token = jwt.encode({"token_use": "access"}, "secret", algorithm="HS256")
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
            self.pair.private,
            algorithm="RS256",
            headers={"kid": self.pair.kid},
        )
        with self._patch_jwks():
            self.assertIsNone(utils.validate_jwt(expired, token_type="access"))


class GetAuthConfigTests(SimpleTestCase):
    @override_settings(
        AUTH_TOKEN_REFRESH_URL="/refresh/",
        WAGTAILADMIN_HOME_PATH="/admin/",
        CSRF_COOKIE_NAME="csrftoken",
        CSRF_HEADER_NAME="HTTP_X_CSRFTOKEN",
        LOGOUT_REDIRECT_URL="/logged-out/",
        SESSION_RENEWAL_OFFSET_SECONDS=30,
        ID_TOKEN_COOKIE_NAME="id",
    )
    def test_json_config_contains_expected_keys(self):
        config_json = utils.get_auth_config()
        data = json.loads(config_json)
        expected_keys = {
            "authTokenRefreshUrl",
            "wagtailAdminHomePath",
            "csrfCookieName",
            "csrfHeaderName",
            "logoutRedirectUrl",
            "sessionRenewalOffsetSeconds",
            "idTokenCookieName",
        }
        self.assertEqual(expected_keys, set(data.keys()))


class JWKSCacheTests(SimpleTestCase):
    def test_jwks_cached(self):
        response = DummyResponse({"foo": "bar"})
        with mock.patch("cms.auth.utils.requests.get", return_value=response) as mock_get:
            utils.get_jwks()
            utils.get_jwks()
            self.assertEqual(mock_get.call_count, 1)  # cached second time
