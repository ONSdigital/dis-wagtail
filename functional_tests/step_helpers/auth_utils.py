import base64
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from behave.runner import Context
from django.conf import settings

from cms.auth import utils as auth_utils
from cms.auth.tests.helpers import CognitoTokenTestCase, generate_rsa_keypair


class AuthenticationTestHelper:
    """Helper class for managing authentication test setup and assertions."""

    def __init__(self, context: Context) -> None:
        self.context = context
        self.setup_test_keypair()

    def setup_test_keypair(self) -> None:
        """Generate and configure test keypair for JWT validation."""
        self.context.test_keypair = generate_rsa_keypair()
        public_b64 = base64.b64encode(self.context.test_keypair.public_der).decode()
        self.context.test_jwks = {self.context.test_keypair.kid: public_b64}

        # Store original get_jwks function
        self.context.original_get_jwks = auth_utils.get_jwks

        # Mock get_jwks to return our test JWKS
        auth_utils.get_jwks = lambda: self.context.test_jwks

    def generate_and_set_tokens(self, groups: list[str] | None = None, **jwt_overrides: dict[str, Any]) -> None:
        """Generate test JWT tokens with specified groups."""
        if groups is None:
            groups = ["role-admin"]

        # Create unique user UUID
        self.context.user_uuid = str(uuid.uuid4())

        # Create helper instance with our test keypair
        token_helper = CognitoTokenTestCase()
        token_helper.keypair = self.context.test_keypair
        token_helper.user_uuid = self.context.user_uuid

        # Generate tokens
        access_token, id_token = token_helper.generate_tokens(groups=groups, **jwt_overrides)

        # Store tokens in context
        self.context.access_token = access_token
        self.context.id_token = id_token

    def create_auth_cookies(self) -> list[dict[str, str | bool]]:
        """Create authentication cookies configuration."""
        return [
            {
                "name": settings.ACCESS_TOKEN_COOKIE_NAME,
                "value": self.context.access_token,
                "domain": "localhost",
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
            {
                "name": settings.ID_TOKEN_COOKIE_NAME,
                "value": self.context.id_token,
                "domain": "localhost",
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
            {
                "name": settings.CSRF_COOKIE_NAME,
                "value": "test-csrf-token",
                "domain": "localhost",
                "path": "/",
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax",
            },
        ]

    def setup_authenticated_user(self) -> None:
        # Check for scenario tag
        tags = set()
        if hasattr(self.context, "tags"):
            tags = set(self.context.tags)
        elif hasattr(self.context, "scenario") and hasattr(self.context.scenario, "tags"):
            tags = set(self.context.scenario.tags)

        refresh_expiry_seconds = 5 if "refresh_expiry" in tags else None

        now = datetime.now(tz=UTC)
        expiry = {
            "short_expiry": 5,
            "long_expiry": 30,
        }.get(
            next((tag for tag in ("short_expiry", "long_expiry") if tag in tags), None),
            20,
        )
        exp = int((now + timedelta(seconds=expiry)).timestamp())

        self.generate_and_set_tokens(groups=["role-admin"], exp=exp)

        cookies = self.create_auth_cookies()
        self.context.page.context.add_cookies(cookies)
        self.setup_session_renewal_timing(refresh_expiry=refresh_expiry_seconds)

    def decode_jwt_payload(self, token: str) -> dict[str, Any]:
        """Decode JWT payload to extract claims."""
        payload_b64 = token.split(".")[1]
        # Pad base64 to correct length
        payload_b64 += "=" * (-len(payload_b64) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded)

    def setup_session_renewal_timing(self, refresh_expiry: int | None = None) -> None:
        """Configure session renewal timing based on JWT expiration."""
        # Decode the expiration time from JWT
        payload = self.decode_jwt_payload(self.context.access_token)
        exp_seconds = payload["exp"]  # UNIX seconds when token expires

        # Calculate millisecond timestamps
        session_ms = exp_seconds * 1000

        # The refresh token expiry is typically much longer (e.g., 12 hours from now)
        if refresh_expiry is not None:
            refresh_expiry_seconds = int((datetime.now() + timedelta(seconds=refresh_expiry)).timestamp())
        else:
            refresh_expiry_seconds = int((datetime.now() + timedelta(hours=12)).timestamp())
        refresh_ms = refresh_expiry_seconds * 1000

        # Store in context for use in the mock
        self.context.refresh_expiry_time = refresh_ms

        # This will be done by the upstream service prior to navigating to Wagtail.
        # The upstream authentication service is responsible for setting the 'dis_auth_client_state' value in
        # localStorage before the user is redirected or navigates to Wagtail.
        # This manual step is only required in tests to simulate the authenticated state
        # that would normally be established by the upstream service.
        self.context.page.context.add_init_script(
            f"""
            window.localStorage.setItem('dis_auth_client_state', JSON.stringify({{
            session_expiry_time: {session_ms},
            refresh_expiry_time: {refresh_ms}
          }}));
        """
        )


def get_cognito_overridden_settings() -> dict:
    """Get Django settings overrides for Cognito tests."""
    return {
        # Core settings
        "AWS_COGNITO_LOGIN_ENABLED": True,
        "AWS_COGNITO_APP_CLIENT_ID": "test-client-id",
        "AWS_REGION": "eu-west-2",
        "AWS_COGNITO_USER_POOL_ID": "test-pool",
        "IDENTITY_API_BASE_URL": "https://cognito-idp.eu-west-2.amazonaws.com/test-pool",
        # Auth settings
        "AUTH_TOKEN_REFRESH_URL": "/refresh/",
        "SESSION_RENEWAL_OFFSET_SECONDS": 5,
        "WAGTAIL_CORE_ADMIN_LOGIN_ENABLED": True,
        "WAGTAILADMIN_HOME_PATH": "admin/",
    }


def capture_request(context: Context) -> None:
    """Capture requests and mock specific endpoints for Cognito-enabled scenarios."""

    def _capture(route: Any, request: Any) -> None:
        context._requests.append(request)  # pylint: disable=protected-access

        # Mock the refresh endpoint for PUT or POST requests
        if request.url.endswith("/refresh/") and request.method in ["POST", "PUT"]:
            refresh_expiry_time = getattr(context, "refresh_expiry_time", None)
            now_ms = int(datetime.now().timestamp() * 1000)

            if refresh_expiry_time and now_ms > refresh_expiry_time:
                # Simulate expired refresh token
                route.fulfill(
                    status=401,
                    content_type="application/json",
                    body=json.dumps({"error": "Refresh token expired"}),
                )
            else:
                # Mock successful refresh response
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "expirationTime": int((datetime.now() + timedelta(minutes=15)).timestamp() * 1000),
                            "refreshExpiryTime": int((datetime.now() + timedelta(hours=12)).timestamp() * 1000),
                        }
                    ),
                )

        elif request.url.endswith("/extend-session/") and request.method == "POST":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"status": "success", "message": "Session extended."}),
            )

        else:
            route.continue_()

    return _capture
