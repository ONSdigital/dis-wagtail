import base64
import logging

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from jwt import InvalidTokenError, get_unverified_header
from jwt import decode as jwt_decode
from jwt.exceptions import ExpiredSignatureError

logger = logging.getLogger(__name__)

JWKS_URL = f"{settings.IDENTITY_API_BASE_URL}/jwt-keys"  # Adjust for env config
EXPECTED_ISSUER = f"https://cognito-idp.eu-west-2.amazonaws.com/{settings.AWS_COGNITO_USER_POOL_ID}"
EXPECTED_AUDIENCE = settings.AWS_COGNITO_APP_CLIENT_ID
ALLOWED_TOKENS = ["access", "id"]
ALGORITHMS = ["RS256"]


def _parse_der_public_key(b64_der_key: str):
    der = base64.b64decode(b64_der_key)
    return serialization.load_der_public_key(der, backend=default_backend())


# @memory_cache(60 * 30)
def get_jwks() -> dict:
    """Retrieves and caches JWKS."""
    response = requests.get(JWKS_URL, timeout=5)
    response.raise_for_status()
    jwks_data = response.json()
    return {kid: _parse_der_public_key(b64_der_key) for kid, b64_der_key in jwks_data.items()}


def validate_jwt(token: str, token_type: str) -> dict | None:
    """Validates JWT and returns claims dict if valid, else None."""
    token = token.split(" ")[1] if token.startswith("Bearer ") else token
    additional_required_fields = ["username"] if token_type == "access" else ["cognito:username", "email"]  # noqa: S105

    try:
        header = get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            logging.error("Missing 'kid' in JWT header")
            return None

        public_key = get_jwks().get(kid)
        if not public_key:
            return None

        claims = jwt_decode(
            token,
            key=public_key,
            algorithms=ALGORITHMS,
            issuer=EXPECTED_ISSUER,
            audience=EXPECTED_AUDIENCE,
            options={
                # Explicitly set to True to avoid changes in default behavior
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_sub": True,
                "verify_jti": True,
                "verify_nbf": False,  # Not used by AWS Cognito
                "require": ["token_use", "cognito:groups", *additional_required_fields],
            },
        )

        if claims["token_use"] != token_type:
            logger.error("Invalid token_use claim", extra={"expected": token_type, "actual": claims["token_use"]})
            return None

        return claims

    except ExpiredSignatureError:
        logger.exception("Token has expired", extra={"token_type": token_type})
    except InvalidTokenError:
        logger.exception("Invalid token", extra={"token_type": token_type})
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error decoding token", extra={"token_type": token_type})

    return None
