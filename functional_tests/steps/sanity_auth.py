from behave import given, then, when  # pylint: disable=no-name-in-module
from playwright.sync_api import Request, Route
from cms.auth.tests.helpers import CognitoTokenTestCase
import uuid
from django.conf import settings
from cms.auth.utils import get_auth_config
import json
import base64
from time import sleep


@given("I have valid JWT tokens and I set the authentication cookies")
def create_valid_tokens(context):
    """Create valid JWT tokens for testing."""
    print("\n=== CREATING JWT TOKENS ===")

    # MOVE REQUEST CAPTURE TO THE BEGINNING - BEFORE ANY NAVIGATION
    """Initialise auth.js request capturing."""
    context._requests = []

    def _capture(route: Route, request: Request):
        context._requests.append(request)
        # Log POST requests to extend-session
        if request.method == "POST" and "extend-session" in request.url:
            print(f"[CAPTURED] POST to {request.url}")
        route.continue_()

    # Capture every network request in this browser context
    context.page.context.route("**/*", _capture)

    # Use the keypair from context (set by @cognito_enabled tag)
    keypair = context.test_keypair
    context.user_uuid = str(uuid.uuid4())

    print(f"User UUID: {context.user_uuid}")
    print(f"Keypair KID: {keypair.kid}")

    # Create helper instance
    helper = CognitoTokenTestCase()
    helper.keypair = keypair
    helper.user_uuid = context.user_uuid

    # Generate tokens with admin role
    access_token, id_token = helper.generate_tokens(groups=["role-admin"])

    print(f"Access Token (first 50 chars): {access_token[:50]}...")
    print(f"ID Token (first 50 chars): {id_token[:50]}...")

    # Store tokens in context
    context.access_token = access_token
    context.id_token = id_token

    print("\n=== SETTING COOKIES ===")

    cookies = [
        {
            "name": settings.ACCESS_TOKEN_COOKIE_NAME,
            "value": context.access_token,
            "domain": "localhost",
            "path": "/",
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax",
        },
        {
            "name": settings.ID_TOKEN_COOKIE_NAME,
            "value": context.id_token,
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

    for cookie in cookies:
        print(f"Setting cookie: {cookie['name']} = {cookie['value'][:50]}...")

    context.page.context.add_cookies(cookies)

    # ——————————————————————————————————————————————————————
    # 2) Decode the 'exp' claim from your test JWT:
    token = context.access_token
    payload_b64 = token.split(".")[1]
    # pad base64 to correct length
    payload_b64 += "=" * (-len(payload_b64) % 4)
    decoded = base64.urlsafe_b64decode(payload_b64)
    payload = json.loads(decoded)
    exp_s = payload["exp"]  # UNIX seconds when token expires

    # ——————————————————————————————————————————————————————
    # 3) Compute your millisecond timestamps:
    cfg = get_auth_config()
    offset_s = cfg["sessionRenewalOffsetSeconds"]
    session_ms = exp_s * 1000
    refresh_ms = session_ms - (offset_s * 1000)
    print(f"Session expiry time: {refresh_ms} ms")

    # ——————————————————————————————————————————————————————
    # 4) Shim Buffer.from and seed localStorage *before* auth.js runs:
    init_js = f"""
    // —— Browser Buffer shim ——
    if (typeof Buffer === 'undefined') {{
      window.Buffer = {{
        from(b64, enc) {{
          if (enc !== 'base64') throw new Error('Unsupported encoding ' + enc);
          const str = b64.replace(/-/g,'+').replace(/_/g,'/');
          return {{
            toString() {{
              return decodeURIComponent(
                atob(str)
                  .split('')
                  .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                  .join('')
              );
            }}
          }};
        }}
      }};
    }}

    // —— Seed auth.js’s timers ——
    window.localStorage.setItem('sessionExpiryTime', '{session_ms}');
    window.localStorage.setItem('refreshExpiryTime','{refresh_ms}');
    """
    context.page.context.add_init_script(init_js)

    # Verify cookies were set
    browser_cookies = context.page.context.cookies()
    print(f"\nBrowser has {len(browser_cookies)} cookies set")
    for cookie in browser_cookies:
        print(f"  - {cookie['name']}: {cookie['value'][:50]}...")


@when("I navigate to the admin page")
def navigate_to_admin(context):
    """Navigate to the Wagtail admin page."""
    context.page.goto(f"{context.base_url}/admin/")

    # Simulate mouse movements to mimic user activity

    # Move mouse to the center of the page
    context.page.mouse.move(500, 300)
    sleep(0.2)

    # Move mouse to another position
    context.page.mouse.move(600, 350)
    sleep(0.2)

    # Move mouse back to original position
    context.page.mouse.move(500, 300)
    sleep(0.2)


@then("a session renewal request should be sent")
def assert_renewal_requested(context):
    cfg = get_auth_config()
    refresh_path = cfg["authTokenRefreshUrl"]

    renewals = [req for req in context._requests if req.method.upper() == "POST" and refresh_path in req.url]

    print(
        f"Captured {len(renewals)} renewal request(s) to {refresh_path} out of {len(context._requests)} total requests"
    )
    assert renewals, f"No renewal requests to {refresh_path} were captured"
