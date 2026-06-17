import base64
import json
import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from jwt import InvalidTokenError, get_unverified_header
from jwt import decode as jwt_decode
from jwt.exceptions import ExpiredSignatureError

from cms.core.cache import memory_cache

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


logger = logging.getLogger(__name__)


def _parse_der_public_key(b64_der_key: str) -> RSAPublicKey:
    """Parses a Base64 encoded DER public key and returns the public key object."""
    der = base64.b64decode(b64_der_key)
    key = serialization.load_der_public_key(der, backend=default_backend())
    return cast("RSAPublicKey", key)


@memory_cache(60 * 30)
def get_jwks() -> dict[str, str]:
    """Retrieves and caches JSON Web Key Sets (JWKS) for token verification."""
    jwks_url = f"{settings.IDENTITY_API_BASE_URL}/jwt-keys"

    response = requests.get(jwks_url, timeout=settings.HTTP_REQUEST_DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    return cast(dict[str, str], response.json())


def validate_jwt(token: str, token_type: str) -> dict | None:
    """Validates the given JWT and returns its claims if valid, otherwise returns None."""
    token = token.split(" ")[1] if token.startswith("Bearer ") else token
    # Set required fields based on token type.
    extra_fields = ["username", "client_id"] if token_type == "access" else ["cognito:username", "email"]  # noqa: S105

    try:
        return _validate_jwt(token, extra_fields=extra_fields, token_type=token_type)
    except requests.exceptions.RequestException:
        logger.exception("Error fetching JWKS")
    except json.decoder.JSONDecodeError:
        logger.exception("Error decoding JWKS to JSON")
    except ExpiredSignatureError:
        logger.exception("Token has expired", extra={"token_type": token_type})
    except InvalidTokenError:
        logger.exception("Invalid token", extra={"token_type": token_type})
    except Exception:  # pylint: disable=broad-except
        logger.exception("Error decoding token or parsing DER public key", extra={"token_type": token_type})
    return None


def _validate_jwt(token: str, *, extra_fields: Iterable[str], token_type: str) -> dict[str, Any] | None:
    header = get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        logger.error("JWT header missing 'kid'.")
        return None

    jwks = get_jwks()
    public_key_b64 = jwks.get(kid)
    if not public_key_b64:
        logger.error("Public key not found for kid", extra={"kid": kid})
        return None

    expected_issuer = f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.AWS_COGNITO_USER_POOL_ID}"
    expected_audience = settings.AWS_COGNITO_APP_CLIENT_ID
    algorithms = ["RS256"]

    claims: dict[str, Any] = jwt_decode(
        token,
        key=_parse_der_public_key(public_key_b64),
        algorithms=algorithms,
        issuer=expected_issuer,
        # aud is not present in access token
        audience=expected_audience if token_type == "id" else None,  # noqa: S105
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_aud": token_type == "id",  # noqa: S105  aud is not present in access token
            "verify_iss": True,
            "verify_sub": True,
            "verify_jti": True,
            "verify_nbf": False,  # AWS Cognito does not utilise 'nbf'
            "require": ["token_use", *extra_fields],
        },
    )

    if claims["token_use"] != token_type:
        logger.error("Invalid token_use claim", extra={"expected": token_type, "actual": claims["token_use"]})
        return None

    return claims


def get_auth_config() -> dict[str, Any]:
    """Returns a dictionary containing authentication configuration details."""
    # Default value for csrf_header_name is "HTTP_X_CSRFTOKEN", the header needs to be set as "X-CSRFToken"
    # Django will convert the header to "HTTP_X_CSRFTOKEN" when it is received
    # @see: https://docs.djangoproject.com/en/5.1/ref/settings/#csrf-header-name
    csrf_header_name = settings.CSRF_HEADER_NAME.replace("HTTP_", "").replace("_", "-")
    return {
        "authTokenRefreshUrl": settings.AUTH_TOKEN_REFRESH_URL,
        "wagtailAdminHomePath": settings.WAGTAILADMIN_HOME_PATH,
        "csrfCookieName": settings.CSRF_COOKIE_NAME,
        "csrfHeaderName": csrf_header_name,
        "sessionRenewalOffsetSeconds": settings.SESSION_RENEWAL_OFFSET_SECONDS,
        "idTokenCookieName": settings.ID_TOKEN_COOKIE_NAME,
    }
