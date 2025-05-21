import json
import time

from behave import given, then, when  # pylint: disable=no-name-in-module
from playwright.sync_api import Request, Route

AUTH_CONFIG = {
    "wagtailAdminHomePath": "admin/",
    "csrfCookieName": "csrftoken",
    "csrfHeaderName": "X-CSRFTOKEN",
    "sessionRenewalOffsetSeconds": 3,  # short so scenario runs fast
    "authTokenRefreshUrl": "/refresh/",
    "idTokenCookieName": "id",
}


# Initialisation STEP runs in Background after page is live
@given("auth.js is initialised on the live page")
def init_auth_js(context):
    page = context.page  # supplied by environment.py
    cfg_json = json.dumps(AUTH_CONFIG)

    page.add_init_script(
        f"""
        window.authConfig = {cfg_json};
        document.cookie = "id=fakeidtoken; path=/";
        document.cookie = "csrftoken=fakecsrftoken; path=/";
        """
    )

    # inject compiled auth.js from staticfiles
    page.add_script_tag(url="/static/js/auth.js")

    # stub token-refresh endpoint
    context.browser_context.route(
        AUTH_CONFIG["authTokenRefreshUrl"],
        lambda route: route.fulfill(status=200, body="{{}}"),
    )

    # capture all subsequent requests in list on context
    context._requests: list[Request] = []

    def _rec(route: Route, request: Request):
        context._requests.append(request)
        route.continue_()

    context.browser_context.route("**/*", _rec)


# Keep alive
@when("the passive renewal timer fires")
def wait_passive_interval(context):
    time.sleep(AUTH_CONFIG["sessionRenewalOffsetSeconds"] + 0.5)


@then('the browser must have made a POST request to "/admin/extend-session/"')
def assert_extend_called(context):
    url_suffix = "/admin/extend-session/"
    matches = [r for r in context._requests if r.url.endswith(url_suffix) and r.method == "POST"]
    assert matches, f"extend-session not called; captured {[r.url for r in context._requests]}"
    hdr = AUTH_CONFIG["csrfHeaderName"]
    assert matches[0].headers[hdr] == "fakecsrftoken"


# Preview pane
@given('the user clicks "Preview" in the Wagtail editor')
def open_preview_iframe(context):
    # the editor tab is still open in another page; open preview in new tab
    context.page.get_by_role("button", name="Preview").click()
    # Wait for iframe to appear in same tab
    iframe = context.page.frame_locator("iframe").frame()
    context.preview_frame = iframe

    # record its network traffic separately
    context.iframe_requests: list[Request] = []

    def _if_rec(route: Route, req: Request):
        context.iframe_requests.append(req)
        route.continue_()

    iframe.page.context.route("**/*", _if_rec)


@then("auth.js is not initialised in the iframe")
def iframe_not_initialised(context):
    frame = context.preview_frame
    initialised = frame.evaluate("() => Boolean(window.SessionManagement?.__INITIALISED__)")
    assert initialised is False, "auth.js unexpectedly initialised inside preview iframe"


@then("no network traffic occurs from the iframe")
def iframe_no_traffic(context):
    # allow the initial HTML fetch only
    assert len(context.iframe_requests) == 0, f"unexpected traffic: {[r.url for r in context.iframe_requests]}"
