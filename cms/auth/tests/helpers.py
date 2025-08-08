import base64
import json
import uuid
from collections import namedtuple
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings

from cms.auth import utils as auth_utils
from cms.users.models import User

RSAKeyPair = namedtuple("RSAKeyPair", ["private", "public_der", "kid"])


def generate_rsa_keypair() -> RSAKeyPair:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    kid = "kid-test"
    return RSAKeyPair(private, public_der, kid)


def build_jwt(pair: RSAKeyPair, *, token_use: str, **extra) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "iss": "https://cognito-idp.eu-west-2.amazonaws.com/test-pool",
        "exp": int((now + timedelta(seconds=30)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": f"jti-{token_use}",
        "token_use": token_use,
        **extra,
    }
    return jwt.encode(  # pyjwt
        payload,
        key=pair.private,
        algorithm="RS256",
        headers={"kid": pair.kid},
    )


class DummyResponse:
    """Tiny helper for mocking requests.get()."""

    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def json(self):
        if isinstance(self._data, str):
            return json.loads(self._data)
        return self._data

    def raise_for_status(self):
        status_code = 400

        if self.status_code >= status_code:
            raise requests.HTTPError(f"HTTP {self.status_code}")


@override_settings(
    AWS_COGNITO_LOGIN_ENABLED=True,
    AWS_COGNITO_APP_CLIENT_ID="test-client-id",
    AWS_REGION="eu-west-2",
    AWS_COGNITO_USER_POOL_ID="test-pool",
    IDENTITY_API_BASE_URL="https://cognito-idp.eu-west-2.amazonaws.com/test-pool",
    ACCESS_TOKEN_COOKIE_NAME="access",
    ID_TOKEN_COOKIE_NAME="id",
    WAGTAIL_CORE_ADMIN_LOGIN_ENABLED=True,
    WAGTAILADMIN_HOME_PATH="/admin/",
    SESSION_RENEWAL_OFFSET_SECONDS=300,
)
class CognitoTokenTestCase(TestCase):
    """Utilities reused by every auth-related TestCase."""

    @classmethod
    def setUpTestData(cls):
        cls.user_uuid: str = str(uuid.uuid4())

        # RSA keypair and JWKS stub
        cls.keypair = generate_rsa_keypair()
        public_b64 = base64.b64encode(cls.keypair.public_der).decode()
        cls.jwks = {cls.keypair.kid: public_b64}

        # Stub JWKS fetch
        auth_utils.get_jwks = lambda: cls.jwks

    def generate_tokens(
        self,
        *,
        username: str | None = None,
        groups: list[str] | None = None,
        client_id: str | None = None,
        **jwt_overrides,
    ) -> tuple[str, str]:
        username = username or self.user_uuid
        client_id = client_id or settings.AWS_COGNITO_APP_CLIENT_ID

        access = build_jwt(
            self.keypair,
            token_use="access",
            username=username,
            client_id=client_id,
            **jwt_overrides,
        )

        id_payload: dict[str, str | list[str]] = {
            "cognito:username": username,
            "email": f"{username}@example.com",
            "given_name": "First",
            "family_name": "Last",
        }
        if groups is not None:
            id_payload["cognito:groups"] = groups

        id_token = build_jwt(
            self.keypair,
            token_use="id",
            aud=client_id,
            **id_payload,
            **jwt_overrides,
        )

        return f"Bearer {access}", id_token

    def set_jwt_cookies(self, access_token: str, id_token: str) -> None:
        client: Client = self.client
        client.cookies[settings.ACCESS_TOKEN_COOKIE_NAME] = access_token
        client.cookies[settings.ID_TOKEN_COOKIE_NAME] = id_token

    def login_with_tokens(self, **token_kwargs: Any) -> None:
        access, id_token = self.generate_tokens(**token_kwargs)
        self.set_jwt_cookies(access, id_token)

    def assertLoggedOut(self, redirect="/admin/login/") -> None:  # pylint: disable=invalid-name
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        self.assertEqual(response.status_code, 302)
        self.assertIn(redirect, response["Location"])
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def assertLoggedIn(self) -> None:  # pylint: disable=invalid-name
        response = self.client.get(settings.WAGTAILADMIN_HOME_PATH)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        # User should now exist after login
        self.assertTrue(User.objects.filter(external_user_id=response.wsgi_request.user.external_user_id).exists())

    def assertInGroups(self, *group_names) -> None:  # pylint: disable=invalid-name
        user = User.objects.get(external_user_id=self.user_uuid)
        for name in group_names:
            self.assertTrue(
                Group.objects.filter(name=name, user=user).exists(),
                f"User should belong to group '{name}'",
            )
