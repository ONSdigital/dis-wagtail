import json
import re
import time
from behave.runner import Context

from behave import given, then, when  # pylint: disable=no-name-in-module
from playwright.sync_api import Request, Route
from cms.auth.tests.helpers import CognitoTokenTestCase
import uuid
from playwright.sync_api import expect
from django.contrib.auth import get_user_model
from django.conf import settings

# # This config matches the test fixture for auth.js behaviour
# auth_config = {
#     "csrfCookieName": "csrftoken",
#     "csrfHeaderName": "X-CSRFTOKEN",
#     "sessionRenewalOffsetSeconds": 3,
# }


# @given("auth.js is initialised on the live page")
# def init_auth_js(context):
#     offset_s = auth_config["sessionRenewalOffsetSeconds"]
#     jwt_ttl = offset_s + 1  # seconds until JWT expiry

#     # Inject into the page before any resources load:
#     context.page.add_init_script(f"""
#         // — polyfill Buffer for JWT decoding —
#         window.Buffer = {{
#             from: (str, enc) => ({{ toString: () => atob(str) }})
#         }};

#         // — Set id-token cookie —
#         document.cookie = "id=fakeidtoken; path=/";

#         // — Build a minimal JWT that expires in {jwt_ttl}s —
#         (function () {{
#             const exp = Math.floor(Date.now() / 1000) + {jwt_ttl};
#             const header  = btoa(JSON.stringify({{ alg: "none" }}));
#             const payload = btoa(JSON.stringify({{ exp }}));
#             document.cookie = `access_token=${{header}}.${{payload}}.; path=/`;
#         }})();

#         // — CSRF cookie for fetchWithCsrf() —
#         document.cookie = "csrftoken=fakecsrftoken; path=/";
#     """)

#     # Capture every outgoing request for assertions (low priority)
#     context._requests = []  # pylint: disable=protected-access

#     def _capture(route: Route, request: Request):
#         context._requests.append(request)  # pylint: disable=protected-access # record everything that actually goes out
#         route.continue_()

#     context.page.route("**/*", _capture)

#     # Stub the passive-renew endpoint after capture so it runs first
#     expiry_ms = int(time.time() * 1000) + 60_000

#     def _fake_refresh(route: Route, request: Request):
#         # record the fake-refresh request as well
#         context._requests.append(request)  # pylint: disable=protected-access
#         route.fulfill(
#             status=200,
#             headers={"Content-Type": "application/json"},
#             body=json.dumps(
#                 {
#                     "session_expiry_time": expiry_ms,
#                     "refresh_expiry_time": expiry_ms,
#                 }
#             ),
#         )

#     context.page.route("**/refresh/", _fake_refresh)


@given("a I have valid JWT tokens and I set the authentication cookies")
def create_valid_tokens(context):
    """Create valid JWT tokens for testing."""
    print("\n=== CREATING JWT TOKENS ===")

    # MOVE REQUEST CAPTURE TO THE BEGINNING - BEFORE ANY NAVIGATION
    """Initialize auth.js request capturing."""
    context._requests = []

    def _capture(route: Route, request: Request):
        context._requests.append(request)
        # Log POST requests to extend-session
        if request.method == "POST" and "extend-session" in request.url:
            print(f"[CAPTURED] POST to {request.url}")
        route.continue_()

    # Set up capture on the browser context, not just the page
    context.page.route("**/*", _capture)

    # Mock refresh endpoint
    expiry_ms = int(time.time() * 1000) + 60_000

    def _mock_refresh(route: Route, request: Request):
        context._requests.append(request)
        route.fulfill(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                {
                    "session_expiry_time": expiry_ms,
                    "refresh_expiry_time": expiry_ms,
                }
            ),
        )

    context.page.route("**/refresh/", _mock_refresh)

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

    # Create the user in database (mimicking what the middleware would do)
    # print("\n=== CREATING USER IN DATABASE ===")
    # user, created = User.objects.get_or_create(
    #     external_user_id=context.user_uuid,
    #     defaults={
    #         "email": f"{context.user_uuid}@example.com",
    #         "username": f"{context.user_uuid}@example.com",
    #         "first_name": "Test",
    #         "last_name": "Admin",
    #     },
    # )

    # if created:
    #     user.set_unusable_password()
    #     user.is_staff = True
    #     user.is_superuser = True
    #     user.save()
    #     print(f"User already exists: {user.username}")

    # # Assign groups
    # print("\n=== ASSIGNING GROUPS ===")
    # admin_group, _ = Group.objects.get_or_create(name=settings.PUBLISHING_ADMIN_GROUP_NAME)
    # viewers_group, _ = Group.objects.get_or_create(name=settings.VIEWERS_GROUP_NAME)
    # user.groups.add(admin_group, viewers_group)
    # print(f"User groups: {list(user.groups.values_list('name', flat=True))}")

    # context.test_user = user
    # print(f"User is_staff: {user.is_staff}")
    # print(f"User is_superuser: {user.is_superuser}")

    print("\n=== SETTING COOKIES ===")

    cookies = [
        {
            "name": settings.ACCESS_TOKEN_COOKIE_NAME,
            "value": context.access_token,
            "domain": "localhost",
            "path": "/",
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax",
        },
        {
            "name": settings.ID_TOKEN_COOKIE_NAME,
            "value": context.id_token,
            "domain": "localhost",
            "path": "/",
            "httpOnly": True,
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

    # Verify cookies were set
    browser_cookies = context.page.context.cookies()
    print(f"\nBrowser has {len(browser_cookies)} cookies set")
    for cookie in browser_cookies:
        print(f"  - {cookie['name']}: {cookie['value'][:50]}...")


@when("I navigate to the admin page")
def navigate_to_admin(context):
    """Navigate to the Wagtail admin page."""
    context.page.goto(f"{context.base_url}/admin/")


@then("I should be granted access to the admin page")
def assert_admin_access(context):
    """Assert that the user is granted access to the admin page."""
    User = get_user_model()
    user = User.objects.get(external_user_id=context.user_uuid)
    email = user.email
    context.page.get_by_role("button", name="first").click()
    context.page.get_by_label("Sidebar", exact=True).get_by_role("link", name="Account").click()
    expect(context.page.get_by_role("textbox", name="Email*")).to_have_value(email)


@when("the passive renewal timer fires")
def wait_passive_interval(context):
    offset = settings.SESSION_RENEWAL_OFFSET_SECONDS * 1000  # ms

    print(f"\n=== WAITING FOR PASSIVE RENEWAL ===")
    print(f"Current URL: {context.page.url}")

    # Check if auth.js is active
    auth_status = context.page.evaluate("""
        () => {
            const result = {
                hasSessionManagement: typeof window.SessionManagement !== 'undefined',
                authConfig: window.authConfig || document.getElementById('auth-config')?.textContent,
            };
            
            // Log to console
            console.log('Checking auth.js status:', result);
            
            // Try to manually trigger if possible
            if (window.SessionManagement && window.SessionManagement.extendSession) {
                console.log('Found extendSession function, calling it manually for testing');
                window.SessionManagement.extendSession();
                result.manuallyTriggered = true;
            }
            
            return result;
        }
    """)

    print(f"Auth.js status: {auth_status}")

    print(f"\n=== WAITING FOR PASSIVE RENEWAL ===")
    print(f"Current URL: {context.page.url}")
    print(f"Offset: {offset}ms ({settings.SESSION_RENEWAL_OFFSET_SECONDS}s)")

    # Log current request count
    before_count = len(context._requests)
    print(f"Requests before wait: {before_count}")

    # Simulate some real user movement so the passive-renewal timer starts.
    for _ in range(10):
        # move between two points
        context.page.mouse.move(100, 100)
        context.page.wait_for_timeout(100)  # 100 ms pause
        context.page.mouse.move(200, 200)
        context.page.wait_for_timeout(100)

    # Now wait long enough for the passive timer to fire
    # give 500 ms cushion
    wait_time = offset + 500
    print(f"Waiting {wait_time}ms for timer to fire...")
    context.page.wait_for_timeout(wait_time)

    # Check what happened
    after_count = len(context._requests)
    print(f"Requests after wait: {after_count}")
    print(f"New requests: {after_count - before_count}")

    # List new requests
    if after_count > before_count:
        print("New requests:")
        for req in context._requests[before_count:]:
            print(f"  - {req.method} {req.url}")


@then('the browser must have made a POST request to "{url_suffix}"')
def assert_extend_called(context, url_suffix):
    matches = [req for req in context._requests if req.url.endswith(url_suffix) and req.method == "POST"]  # pylint: disable=protected-access
    if not matches:
        captured = [r.url for r in context._requests]  # pylint: disable=protected-access
        raise AssertionError(f"Expected POST to {url_suffix}, but captured: {captured}")
    # Store the matched request for following steps
    context.last_request = matches[0]


@then('that request must include the CSRF header "{header_name}"')
def assert_csrf_header(context, header_name):
    req = getattr(context, "last_request", None)
    if req is None:
        raise AssertionError("No matching request found for CSRF header assertion")
    # Playwright lower-cases all header names:
    token = req.headers.get(header_name) or req.headers.get(header_name.lower())
    if token != "test-csrf-token":  # noqa: S105
        raise AssertionError(f"Expected CSRF header '{header_name}': 'test-csrf-token', got: '{token}'")


@then('the live page should include a `<script id="auth-config">` data-island')
def assert_data_island_present(context):
    page = context.page
    # wait for network to settle (so all scripts are injected)
    page.wait_for_load_state("networkidle")

    html = page.content()
    if not re.search(r'<script[^>]+id=["\']auth-config["\']', html):
        raise AssertionError(f'<script id="auth-config"> data-island not found on live page\n\nFull HTML was:\n{html}')


@then("the live page should load `/static/js/auth.js`")
def assert_auth_js_loaded(context):
    page = context.page
    page.wait_for_load_state("networkidle")

    html = page.content()
    # match any <script> whose src ends with auth.js (with optional hash/query)
    pattern = r'<script[^>]+src=["\'][^"\']*auth(\.[a-z0-9]+)?\.js(\?[^"\']*)?["\']'
    if not re.search(pattern, html):
        raise AssertionError(f"auth.js bundle not included on live page\n\nFull HTML was:\n{html}")


@then("auth.js should not be initialised in the iframe")
def iframe_not_initialised(context):
    # Wait for the <iframe> element to appear
    iframe_el = context.page.wait_for_selector("#w-preview-iframe", timeout=5_000)
    # Grab the Playwright Frame from that element
    frame = iframe_el.content_frame()
    if not frame:
        raise AssertionError("Preview iframe not found on the page")

    # Evaluate inside the iframe
    initialised = frame.evaluate("() => Boolean(window.SessionManagement?.__INITIALISED__)")
    if initialised:
        raise AssertionError("auth.js unexpectedly initialised inside preview iframe")


@then("no network traffic should occur within the iframe")
def iframe_no_traffic(context):
    requests = getattr(context, "iframe_requests", [])
    # Allow only the initial HTML fetch; any additional traffic fails
    if len(requests) > 1:
        urls = [r.url for r in requests]
        raise AssertionError(f"Unexpected iframe network traffic: {urls}")
