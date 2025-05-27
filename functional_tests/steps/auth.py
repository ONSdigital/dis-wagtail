import json
import re
import time

from behave import given, then, when  # pylint: disable=no-name-in-module
from playwright.sync_api import Request, Route

# This config matches the test fixture for auth.js behaviour
auth_config = {
    "csrfCookieName": "csrftoken",
    "csrfHeaderName": "X-CSRFTOKEN",
    "sessionRenewalOffsetSeconds": 3,
}


@given("auth.js is initialised on the live page")
def init_auth_js(context):
    offset_s = auth_config["sessionRenewalOffsetSeconds"]
    jwt_ttl = offset_s + 1  # seconds until JWT expiry

    # Inject into the page before any resources load:
    context.page.add_init_script(f"""
        // — polyfill Buffer for JWT decoding —
        window.Buffer = {{
            from: (str, enc) => ({{ toString: () => atob(str) }})
        }};

        // — Set id-token cookie —
        document.cookie = "id=fakeidtoken; path=/";

        // — Build a minimal JWT that expires in {jwt_ttl}s —
        (function () {{
            const exp = Math.floor(Date.now() / 1000) + {jwt_ttl};
            const header  = btoa(JSON.stringify({{ alg: "none" }}));
            const payload = btoa(JSON.stringify({{ exp }}));
            document.cookie = `access_token=${{header}}.${{payload}}.; path=/`;
        }})();

        // — CSRF cookie for fetchWithCsrf() —
        document.cookie = "csrftoken=fakecsrftoken; path=/";
    """)

    # Capture every outgoing request for assertions (low priority)
    context._requests = []  # pylint: disable=protected-access

    def _capture(route: Route, request: Request):
        context._requests.append(request)  # pylint: disable=protected-access # record everything that actually goes out
        route.continue_()

    context.page.route("**/*", _capture)

    # Stub the passive-renew endpoint after capture so it runs first
    expiry_ms = int(time.time() * 1000) + 60_000

    def _fake_refresh(route: Route, request: Request):
        # record the fake-refresh request as well
        context._requests.append(request)  # pylint: disable=protected-access
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

    context.page.route("**/refresh/", _fake_refresh)


@when("the passive renewal timer fires")
def wait_passive_interval(context):
    offset = auth_config["sessionRenewalOffsetSeconds"] * 1000  # ms

    # Simulate some real user movement so the passive-renewal timer starts.
    for _ in range(10):
        # move between two points
        context.page.mouse.move(100, 100)
        context.page.wait_for_timeout(100)  # 100 ms pause
        context.page.mouse.move(200, 200)
        context.page.wait_for_timeout(100)

    # Now wait long enough for the passive timer to fire
    # give 500 ms cushion
    context.page.wait_for_timeout(offset + 500)


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
    if token != "fakecsrftoken":  # noqa: S105
        raise AssertionError(f"Expected CSRF header '{header_name}': 'fakecsrftoken', got: '{token}'")


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
