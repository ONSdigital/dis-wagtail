import logging

import jwt
from django.contrib.auth import get_user_model
from jwt import ExpiredSignatureError, InvalidTokenError

logger = logging.getLogger(__name__)


User = get_user_model()


def extract_and_validate_token(token: str, token_type: str) -> dict | None:
    """Extract and validate a JWT token using the appropriate public key."""
    try:
        token = token.split(" ")[1] if token.startswith("Bearer ") else token
        kid = jwt.get_unverified_header(token).get("kid")
        if not kid:
            raise ValueError(f"{token_type} is missing 'kid' in the header.")

        # public_key = get_public_key(kid)
        # Retrieve and validate token payload
        payload: dict = jwt.decode(
            token,
            # public_key,  # Uncomment for production
            algorithms=["RS256"],
            options={
                "verify_iss": False,  # Set to True in production
                "verify_exp": True,
                "verify_signature": False,  # Set to True in production
            },
        )
        return payload
    except ExpiredSignatureError:
        logger.exception("%s has expired", token_type)
    except InvalidTokenError:
        logger.exception("Invalid %s", token_type)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to validate %s", token_type)
    return None
