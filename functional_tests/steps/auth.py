import time

from behave import given, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.conf import settings
from playwright.sync_api import expect

from cms.auth.utils import get_auth_config
from functional_tests.step_helpers.auth_utils import AuthenticationTestHelper
from functional_tests.step_helpers.utils import require_request


@given("the user is authenticated")
def create_valid_tokens(context: Context) -> None:
    """Set up valid JWT tokens and authentication cookies for testing."""
    helper = AuthenticationTestHelper(context)
    helper.setup_test_keypair()
    helper.generate_test_tokens(groups=["role-admin"])
    cookies = helper.create_auth_cookies()
    context.page.context.add_cookies(cookies)
    helper.setup_session_renewal_timing()


@when("the user navigates to the admin page")
def navigate_to_admin(context: Context) -> None:
    """Navigate to the Wagtail admin page and simulate user activity."""
    # Navigate to admin
    context.page.goto(f"{context.base_url}/admin/")


@when("the user becomes active again")
@when("the user is active in the admin interface")
@when("the JWT token is refreshed in one tab")
def simulate_user_activity(context: Context) -> None:
    """Simulate mouse movements to trigger activity detection."""
    movements = [(500, 300), (600, 350), (500, 300)]

    for x, y in movements:
        context.page.mouse.move(x, y)
        time.sleep(3)

    time.sleep(5)  # Allow time for any session renewal logic to run


@then("a session renewal request should be sent")
def verify_renewal_requested(context: Context) -> None:
    auth_config = get_auth_config()
    refresh_path = auth_config["authTokenRefreshUrl"]

    require_request(
        context._requests,  # pylint: disable=protected-access
        lambda r: "/extend-session/" in r.url and r.method in ("POST", "PUT"),
        "extend_session view call",
    )
    require_request(
        context._requests,  # pylint: disable=protected-access
        lambda r: refresh_path in r.url and r.method in ("POST", "PUT"),
        f"renewal request to {refresh_path}",
    )


@given("the user has no valid JWT tokens")
def step_clear_tokens(context: Context) -> None:
    """Clear any existing auth cookies (no valid tokens)."""
    context.page.context.clear_cookies()


@then("the logout request should complete successfully")
@then("the user should be redirected to the sign-in page")
def step_redirected_to_signin(context: Context) -> None:
    """Verify we were redirected to the admin login page."""
    expected_path = "/admin/login/"
    current_url = context.page.url
    if expected_path not in current_url:
        raise AssertionError(f"Not redirected to login, current URL: {current_url}")


@then("the user should not be redirected to the sign-in page")
def step_not_redirected_to_signin(context: Context) -> None:
    """Verify we stayed on admin and did not hit the login URL."""
    forbidden = "/admin/login/"
    current = context.page.url
    if forbidden in current:
        raise AssertionError(f"Unexpected redirect to login page: {current}")


@when("the user remains inactive for a period longer than the token's expiration time")
def step_wait_for_expiry(context: Context) -> None:  # pylint: disable=unused-argument
    """Sleep past the token TTL so it expires."""
    time.sleep(20)


@given("the user refreshes the page")
def step_refresh_page(context: Context) -> None:
    """Reload the current page."""
    context.page.reload()


@when('the user clicks the "Log out" button in the Wagtail UI')
def step_click_logout(context: Context) -> None:
    """Trigger the logout flow."""
    context.page.get_by_role("button", name="first").click()
    context.page.get_by_role("button", name="Log out").click()


@then("the tokens should be cleared from the browser")
def step_tokens_cleared(context: Context) -> None:
    """Verify that access, id, and session tokens are no longer present in cookies."""
    token_names = [
        getattr(settings, "ACCESS_TOKEN_COOKIE_NAME", "access_token"),
        getattr(settings, "ID_TOKEN_COOKIE_NAME", "id_token"),
        getattr(settings, "SESSION_COOKIE_NAME", "sessionid"),
    ]
    cookies = context.page.context.cookies()
    present = [name for name in token_names if any(cookie["name"] == name for cookie in cookies)]
    if present:
        seen = ", ".join(f"{c['name']}={c.get('value', '')}" for c in cookies)
        raise AssertionError(f"Expected tokens to be cleared but found still present: {present}. All cookies: {seen}")


@when("the user opens a second tab")
def step_two_tabs(context: Context) -> None:
    """Ensure two pages share the same session context."""
    # first tab is context.page
    page_1 = context.page
    # open a second tab
    page_2 = context.page.context.new_page()
    page_2.goto(f"{context.base_url}/admin/")

    context.pages = [page_1, page_2]


# @when("the JWT token is refreshed in one tab")
# def step_refresh_token_and_extend_session(context: Context) -> None:
#     """Simulate mouse movements in Tab 1 to trigger JWT token refresh and session extension."""
#     movements = [(500, 300), (600, 350), (500, 300)]

#     page_1 = context.pages[0]
#     for x, y in movements:
#         page_1.mouse.move(x, y)
#         time.sleep(3)

#     time.sleep(5)  # Allow time for any session renewal logic to run


# @when("the JWT token is refreshed in one tab")
# def step_refresh_in_one_tab(context: Context) -> None:
#     """Trigger renewal in Tab 1, sync state into Tab 2, and capture both expiries."""
#     tab1_logs, tab2_logs = [], []

#     # Listen on both pages before we do anything
#     context.pages[0].on("console", lambda msg: tab1_logs.append(msg.text))
#     context.pages[1].on("console", lambda msg: tab2_logs.append(msg.text))

#     # Kick off the activity-based renewal
#     movements = [(500, 300), (600, 350), (500, 300)]
#     for x, y in movements:
#         context.pages[0].mouse.move(x, y)
#         time.sleep(3)

#     # Give the library a moment to log the result
#     time.sleep(1)

#     # Extract Tab 1's “new expiration time”
#     for text in tab1_logs:
#         print(f"Tab 1 log: {text}")
#         m = re.search(r"new expiration time: (\d+)", text)
#         if m:
#             context.first_tab_expiry = m.group(1)
#             break
#     else:
#         raise AssertionError("No renewal log in Tab 1; saw:\n  " + "\n  ".join(tab1_logs))

#     # Pull the fresh state from Tab 1's localStorage
#     state = context.pages[0].evaluate("localStorage.getItem('dis_auth_client_state')")

#     #    Copy that into Tab 2 and fire a StorageEvent so its listener runs
#     context.pages[1].evaluate(
#         f"""
#         localStorage.setItem('dis_auth_client_state', {json.dumps(state)});
#         window.dispatchEvent(new StorageEvent('storage', {{
#             key: 'dis_auth_client_state',
#             newValue: {json.dumps(state)}
#         }}));
#         """
#     )

#     # Let Tab 2's listener fire and log
#     time.sleep(1)

#     # Extract Tab 2's “new expiration time”
#     for text in tab2_logs:
#         m = re.search(r"new expiration time: (\d+)", text)
#         print(f"Tab 2 log: {text}")
#         if m:
#             context.second_tab_expiry = m.group(1)
#             break
#     else:
#         raise AssertionError("No renewal log in Tab 2; saw:\n  " + "\n  ".join(tab2_logs))


# @then("the second tab should update its session without a manual reload")
# def step_second_tab_update(context: Context) -> None:
#     """Compare the two captured timestamps."""
#     if context.second_tab_expiry != context.first_tab_expiry:
#         raise AssertionError(f"Timestamps differ: Tab 1={context.first_tab_expiry}, Tab 2={context.second_tab_expiry}")


@when("the user logs out from one tab")
def step_logout_one_tab(context: Context) -> None:
    """Perform logout in Tab 1 by re-using the existing logout click."""
    context.execute_steps("""
        When the user clicks the "Log out" button in the Wagtail UI
    """)


@then("both tabs should remain logged in")
def step_both_tabs_remain_logged_in(context: Context) -> None:
    """Reload both tabs and verify that neither tab is redirected to the login page."""
    forbidden_path = "/admin/login/"
    for i, tab in enumerate(context.pages):
        tab.reload()
        if forbidden_path in tab.url:
            raise AssertionError(f"Tab {i + 1} was unexpectedly redirected to login; URL is {tab.url}")


@when("the user is editing a page")
def step_navigate_iframe(context: Context) -> None:
    """Navigate to the a information page to simulate editing."""
    context.page.goto(f"{context.base_url}/admin/")

    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home English").click()
    context.page.get_by_role("link", name="Add child page").click()
    context.page.get_by_role("link", name="Information page", exact=True).click()
    context.page.get_by_role("textbox", name="Title*").click()
    context.page.get_by_role("textbox", name="Title*").fill("Info page")
    context.page.locator("#panel-child-content-summary-content").get_by_role("textbox").locator("div").nth(2).click()
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Info page summary")
    context.page.get_by_title("Insert a block").click()
    context.page.get_by_text("Section heading").click()
    context.page.locator("#content-0-value").fill("Heading")

    context.session_init_logs = []
    context.page.on(
        "console",
        lambda msg: (
            context.session_init_logs.append(msg.text)
            if "Initialising session management with config" in (msg.text or "")
            else None
        ),
    )

    context.page.get_by_role("button", name="Save draft").click()


@then("the user opens the preview pane and the session should not be initialised in the iframe")
def step_session_not_initialised_in_iframe(context: Context) -> None:
    """Ensure session management only initialises once (in the parent), and not inside the iframe."""
    # open preview
    context.page.get_by_role("button", name="Toggle preview").click()
    iframe = context.page.frame_locator("#w-preview-iframe")
    expect(iframe.get_by_text("Info page", exact=True)).to_be_visible()

    # small pause for any stray logs
    time.sleep(1)

    # now assert we only saw one init-log total
    init_msg = "Initialising session management with config"
    count = len(context.session_init_logs)
    if count != 1:
        raise AssertionError(
            f"Expected exactly one console message “{init_msg}” (in parent only), "
            f"but found {count}: {context.session_init_logs}"
        )
