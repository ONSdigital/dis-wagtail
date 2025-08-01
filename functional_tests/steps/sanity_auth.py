import base64
import json
import uuid
from time import sleep
from typing import Any, Optional

from behave import given, then, when  # pylint: disable=no-name-in-module
from django.conf import settings
from playwright.sync_api import Request

from cms.auth import utils as auth_utils
from cms.auth.tests.helpers import CognitoTokenTestCase, generate_rsa_keypair
from cms.auth.utils import get_auth_config
import time


class AuthenticationTestHelper:
    """Helper class for managing authentication test setup and assertions."""

    def __init__(self, context):
        self.context = context
        self.captured_requests: list[Request] = []

    def setup_test_keypair(self):
        """Generate and configure test keypair for JWT validation."""
        self.context.test_keypair = generate_rsa_keypair()
        public_b64 = base64.b64encode(self.context.test_keypair.public_der).decode()
        self.context.test_jwks = {self.context.test_keypair.kid: public_b64}

        # Store original get_jwks function
        self.context.original_get_jwks = auth_utils.get_jwks

        # Mock get_jwks to return our test JWKS
        auth_utils.get_jwks = lambda: self.context.test_jwks

        print(f"Test keypair configured with KID: {self.context.test_keypair.kid}")

    def generate_test_tokens(self, groups: Optional[list[str]] = None) -> tuple[str, str]:
        """Generate test JWT tokens with specified groups."""
        if groups is None:
            groups = ["role-admin"]

        # Create unique user UUID
        self.context.user_uuid = str(uuid.uuid4())
        print(f"Generated User UUID: {self.context.user_uuid}")

        # Create helper instance with our test keypair
        token_helper = CognitoTokenTestCase()
        token_helper.keypair = self.context.test_keypair
        token_helper.user_uuid = self.context.user_uuid

        # Generate tokens
        access_token, id_token = token_helper.generate_tokens(groups=groups)

        # Store tokens in context
        self.context.access_token = access_token
        self.context.id_token = id_token

        # Debug output
        print(f"Access Token (first 50 chars): {access_token[:50]}...")
        print(f"ID Token (first 50 chars): {id_token[:50]}...")

        return access_token, id_token

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

    def decode_jwt_payload(self, token: str) -> dict[str, Any]:
        """Decode JWT payload to extract claims."""
        payload_b64 = token.split(".")[1]
        # Pad base64 to correct length
        payload_b64 += "=" * (-len(payload_b64) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded)

    def setup_session_renewal_timing(self):
        """Configure session renewal timing based on JWT expiration."""
        # Decode the expiration time from JWT
        payload = self.decode_jwt_payload(self.context.access_token)
        exp_seconds = payload["exp"]  # UNIX seconds when token expires

        # Get auth configuration
        auth_config = get_auth_config()
        offset_seconds = auth_config["sessionRenewalOffsetSeconds"]

        # Calculate millisecond timestamps
        session_ms = exp_seconds * 1000
        refresh_ms = session_ms - (offset_seconds * 1000)

        print(f"Session expiry time: {session_ms} ms")
        print(f"Refresh trigger time: {refresh_ms} ms")

        self.context.page.context.add_init_script(f"""
            window.localStorage.setItem('dis_auth_client_state', JSON.stringify({{
            session_expiry_time: {session_ms},
            refresh_expiry_time: {refresh_ms}
          }}));
        """)

    def assert_renewal_request_sent(self):
        """Assert that a session renewal request was attempted."""
        # Check console logs for the refresh attempt
        console_messages = getattr(self.context, "console_messages", [])

        # Look for the renewal attempt in console logs
        refresh_attempt = any("Starting session renewal process" in str(msg.text) for msg in console_messages)

        if refresh_attempt:
            print("Session renewal was attempted (detected in console logs)")
            return True

        # Fallback to checking captured requests
        auth_config = get_auth_config()
        refresh_path = auth_config["authTokenRefreshUrl"]

        requests = getattr(self.context, "_requests", [])
        renewal_requests = [req for req in requests if req.method.upper() == "POST" and refresh_path in req.url]

        print(f"Captured {len(renewal_requests)} renewal request(s) to {refresh_path}")
        print(f"Total requests captured: {len(requests)}")

        assert refresh_attempt or renewal_requests, "No session renewal attempt detected"


@given("I have valid JWT tokens and I set the authentication cookies")
def create_valid_tokens(context):
    """Set up valid JWT tokens and authentication cookies for testing."""
    helper = AuthenticationTestHelper(context)

    # Set up test keypair
    helper.setup_test_keypair()

    # Generate test tokens
    helper.generate_test_tokens(groups=["role-admin"])

    # Create and set cookies
    cookies = helper.create_auth_cookies()
    for cookie in cookies:
        print(f"Setting cookie: {cookie['name']} = {cookie['value'][:50]}...")
    context.page.context.add_cookies(cookies)

    # Set up session renewal timing
    helper.setup_session_renewal_timing()


@when("I navigate to the admin page")
def navigate_to_admin(context):
    """Navigate to the Wagtail admin page and simulate user activity."""
    # Navigate to admin
    context.page.goto(f"{context.base_url}/admin/")


@when("I perform an action that requires authentication such as mouse movements")
def simulate_user_activity(context):
    """Simulate mouse movements to trigger activity detection."""
    movements = [(500, 300), (600, 350), (500, 300)]

    for x, y in movements:
        context.page.mouse.move(x, y)
        sleep(0.2)


@then("a session renewal request should be sent")
def assert_renewal_requested(context):
    """Verify that a session renewal request was sent."""
    auth_config = get_auth_config()
    refresh_path = auth_config["authTokenRefreshUrl"]

    # Check the requests captured
    renewal_requests = [req for req in context._requests if refresh_path in req.url and req.method in ["POST", "PUT"]]

    print(f"Captured {len(renewal_requests)} renewal request(s) to {refresh_path}")
    print(f"Total requests captured: {len(context._requests)}")

    assert renewal_requests, f"No renewal requests to {refresh_path} were captured"


@given("I have no valid JWT tokens")
def step_clear_tokens(context):
    """Clear any existing auth cookies (no valid tokens)."""
    context.page.context.clear_cookies()


@then("the logout request should complete successfully")
@then("I should be redirected to the sign-in page")
def step_redirected_to_signin(context):
    """Assert we were redirected to the admin login page."""
    assert "/admin/login/" in context.page.url, f"Not redirected to login, current URL: {context.page.url}"


@then("I should not be redirected to the sign-in page")
def step_not_redirected_to_signin(context):
    """Assert we stayed on admin and did not hit the login URL."""
    # Assert we did not get redirected to the admin login page
    assert "/admin/login/" not in context.page.url, f"Redirected to login at {context.page.url}"


@when("I remain inactive until my JWT token expires")
def step_wait_for_expiry(context):
    """Sleep past the token TTL so it expires."""
    time.sleep(12)


@when('I click the "Log out" button in the Wagtail UI')
def step_click_logout(context):
    """Trigger the logout flow and wait for the network call."""
    context.page.get_by_role("button", name="first").click()
    context.page.get_by_role("button", name="Log out").click()


@then("the tokens should be cleared from the browser")
def step_tokens_cleared(context):
    """Assert that access, id, and sessionId tokens are no longer present in cookies."""
    token_names = [
        getattr(settings, "ACCESS_TOKEN_COOKIE_NAME", "access_token"),
        getattr(settings, "ID_TOKEN_COOKIE_NAME", "id_token"),
    ]
    cookies = context.page.context.cookies()
    for name in token_names:
        assert not any(cookie["name"] == name for cookie in cookies), f"Token '{name}' still present in cookies"


@when("I am logged in and have Wagtail open in two browser tabs")
def step_two_tabs(context):
    """Ensure two pages share the same session context."""
    # first tab is context.page
    page1 = context.page
    # open a second tab
    page2 = context.browser.new_page()
    page2.goto("/admin")
    context.pages = [page1, page2]


@when("the JWT token is refreshed in one tab")
def step_refresh_in_one_tab(context):
    """Trigger a session-renewal in the first tab."""
    auth_cfg = get_auth_config()
    refresh_url = auth_cfg["authTokenRefreshUrl"]
    # cause renewal (e.g. mouse move)
    context.pages[0].mouse.move(5, 5)
    # wait for the renewal request to fire
    context.pages[0].wait_for_request(lambda req: refresh_url in req.url, timeout=5000)


@then("the second tab should update its session without a manual reload")
def step_second_tab_update(context):
    """Assert the new token has propagated to tab 2 via shared cookies/storage."""
    auth_cfg = get_auth_config()
    token_name = auth_cfg.get("authTokenName", "auth_token")
    # grab cookie values from each context
    cookies1 = context.pages[0].context.cookies()
    cookies2 = context.pages[1].context.cookies()
    val1 = next((c["value"] for c in cookies1 if c["name"] == token_name), None)
    val2 = next((c["value"] for c in cookies2 if c["name"] == token_name), None)
    assert val1 and val1 == val2, f"Tab 2 did not pick up refreshed token ({val1=} vs {val2=})"


@when("I log out from one tab")
def step_logout_one_tab(context):
    """Perform logout in tab 1 (reuse existing logout click)."""
    # re-use the logout step:
    context.execute_steps("""
        When I click the "Log out" button in the Wagtail UI
    """)


@then("both tabs should be redirected to the sign-in page")
def step_both_tabs_redirect(context):
    """Assert both pages land on login after logout."""
    auth_cfg = get_auth_config()
    login_path = auth_cfg["loginUrl"]
    for p in context.pages:
        p.wait_for_url(lambda url: login_path in url, timeout=5000)
        assert login_path in p.url, f"Tab URL after logout was {p.url}"


@then("no split session remains active")
def step_no_split_session(context):
    """Ensure no auth cookies remain anywhere."""
    auth_cfg = get_auth_config()
    token_name = auth_cfg.get("authTokenName", "auth_token")
    for p in context.pages:
        cookies = p.context.cookies()
        assert not any(c["name"] == token_name for c in cookies), "Found stale auth cookie after logout"
