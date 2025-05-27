import re
import time

from behave import given, then, when  # pylint: disable=no-name-in-module
from playwright.sync_api import Request, Route

# This config matches the test fixture for auth.js behavior
auth_config = {
    "wagtailAdminHomePath": "admin/",
    "csrfCookieName": "csrftoken",
    "csrfHeaderName": "X-CSRFTOKEN",
    "sessionRenewalOffsetSeconds": 3,
    "authTokenRefreshUrl": "/refresh/",
    "idTokenCookieName": "id",
}


@given("auth.js is initialised on the live page")
def init_auth_js(context):
    """Stub the token-refresh endpoint and capture outgoing requests
    so we can verify extend-session calls on the real live page.
    The <script id="auth-config"> and auth.js bundle
    come from the real hook when AWS_COGNITO_LOGIN_ENABLED=True.
    """
    # Stub the token-refresh endpoint
    context.browser_context.route(
        auth_config["authTokenRefreshUrl"],
        lambda route: route.fulfill(status=200, body="{}"),
    )

    # Capture all outgoing requests for later inspection
    context.requests = []

    def _capture(route: Route, request: Request):
        context.requests.append(request)
        route.continue_()

    context.browser_context.route("**/*", _capture)


@when("the passive renewal timer fires")
def wait_passive_interval(context):
    # Wait slightly longer than the configured offset
    time.sleep(auth_config["sessionRenewalOffsetSeconds"] + 0.5)


@then('the browser must have made a POST request to "{url_suffix}"')
def assert_extend_called(context, url_suffix):
    matches = [req for req in context.requests if req.url.endswith(url_suffix) and req.method == "POST"]
    if not matches:
        captured = [r.url for r in context.requests]
        raise AssertionError(f"Expected POST to {url_suffix}, but captured: {captured}")
    # Store the matched request for following steps
    context.last_request = matches[0]


@then('that request must include the CSRF header "{header_name}"')
def assert_csrf_header(context, header_name):
    req = getattr(context, "last_request", None)
    if req is None:
        raise AssertionError("No matching request found for CSRF header assertion")
    token = req.headers.get(header_name)
    if token != "fakecsrftoken":  # noqa: S105
        raise AssertionError(f"Expected CSRF header '{header_name}': 'fakecsrftoken', got: '{token}'")


@then('the live page should include a `<script id="auth-config">` data-island')
def assert_data_island_present(context):
    html = context.page.content()
    if '<script id="auth-config"' not in html:
        raise AssertionError('<script id="auth-config"> data-island not found on live page')


@then("the live page should load `/static/js/auth.js`")
def assert_auth_js_loaded(context):
    """Verifies that the auth.js bundle appears on the live page,
    regardless of hashing, query strings, or extra attributes.
    """
    html = context.page.content()
    # Look for a <script> tag whose src contains 'auth.js' at the end
    pattern = r'<script[^>]+src=["\'][^"\']*auth(\.[a-z0-9]+)?\.js(\?[^"\']*)?["\']'
    if not re.search(pattern, html):
        raise AssertionError("auth.js bundle not included on live page; HTML was:\n" + html)


@then("auth.js should not be initialised in the iframe")
def iframe_not_initialised(context):
    # Using stored frame reference if available, or locate by id
    frame = getattr(context, "preview_frame", None) or context.page.frame_locator("#w-preview-iframe").frame()
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
