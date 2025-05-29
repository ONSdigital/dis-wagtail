import json
from collections import namedtuple
from datetime import UTC, datetime, timedelta

import jwt
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

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
        "exp": int((now + timedelta(minutes=5)).timestamp()),
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
