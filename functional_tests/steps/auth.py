# pylint: disable=not-callable
from behave import given, then, when
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
    helper.setup_authenticated_user()


@when("the user navigates to the admin page")
def navigate_to_admin(context: Context) -> None:
    """Navigate to the Wagtail admin page."""
    context.page.goto(f"{context.base_url}/admin/")


@when("the user becomes active again")
@when("the user is active in the admin interface")
@when("the user interacts with the page in one tab")
def simulate_user_activity(context: Context) -> None:
    """Simulate mouse movements to trigger activity detection."""
    movements = [(500, 300), (600, 350), (500, 300), (400, 250)]

    for x, y in movements:
        context.page.mouse.move(x, y)
        context.page.wait_for_timeout(5000)

    context.page.wait_for_timeout(1000)  # Allow time for any session renewal logic to run


@then("their session is extended")
def verify_renewal_requested(context: Context) -> None:
    auth_config = get_auth_config()
    refresh_path = auth_config["authTokenRefreshUrl"]

    require_request(
        context._requests,  # pylint: disable=protected-access
        lambda r: refresh_path in r.url and r.method in ("POST", "PUT"),
        f"renewal request to {refresh_path}",
    )


@given("the user is unauthenticated")
def step_clear_tokens(context: Context) -> None:
    """Clear any existing auth cookies (no valid tokens)."""
    context.page.context.clear_cookies()


@then("the user is logged out")
@then("the user is redirected to the login page")
def step_redirected_to_signin(context: Context) -> None:
    """Verify we were redirected to the admin login page."""
    expected_path = "/admin/login/"
    current_url = context.page.url
    assert expected_path in current_url, f"Not redirected to login, current URL: {current_url}"


@then("the user remains logged in")
@then("the user is not asked to login")
def step_not_redirected_to_signin(context: Context) -> None:
    """Verify we stayed on admin and did not hit the login URL."""
    forbidden = "/admin/login/"
    current = context.page.url
    assert forbidden not in current, f"Unexpected redirect to login page: {current}"


@when("the user remains inactive until the refresh token expires")
@when("the user remains inactive until the session expires")
def step_wait_for_expiry(context: Context) -> None:
    """Sleep past the token TTL so it expires."""
    context.page.wait_for_timeout(5000)


@given("the user refreshes the page")
def step_refresh_page(context: Context) -> None:
    """Reload the current page."""
    context.page.reload()


@when('the user clicks the "Log out" button in the Wagtail UI')
def step_click_logout(context: Context) -> None:
    """Trigger the logout flow."""
    context.page.locator("button.sidebar-footer__account").click()
    context.page.get_by_role("button", name="Log out").click()


@then("all authentication data is cleared in the browser")
def step_tokens_cleared(context: Context) -> None:
    """Verify that access, id, and session tokens are no longer present in cookies."""
    token_names = [
        settings.ACCESS_TOKEN_COOKIE_NAME,
        settings.ID_TOKEN_COOKIE_NAME,
        settings.SESSION_COOKIE_NAME,
    ]
    cookies = context.page.context.cookies()
    present = [name for name in token_names if any(cookie["name"] == name for cookie in cookies)]
    seen = ", ".join(f"{c['name']}={c.get('value', '')}" for c in cookies)
    assert not present, f"Expected tokens to be cleared but found still present: {present}. All cookies: {seen}"


@when("the user opens an admin page in a second tab")
def step_two_tabs(context: Context) -> None:
    """Ensure two pages share the same session context."""
    # first tab is context.page
    page_1 = context.page
    # open a second tab
    page_2 = context.page.context.new_page()
    page_2.goto(f"{context.base_url}/admin/")

    context.pages = [page_1, page_2]


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
        assert forbidden_path not in tab.url, f"Tab {i + 1} was unexpectedly redirected to login; URL is {tab.url}"


@then("both tabs are redirected to the login page")
def step_both_tabs_redirected_to_signin(context: Context) -> None:
    """Reload both tabs and verify that both are redirected to the login page."""
    expected_path = "/admin/login/"
    for i, tab in enumerate(context.pages):
        tab.reload()
        assert expected_path in tab.url, f"Tab {i + 1} was not redirected to login; URL is {tab.url}"


@when("the user opens the preview pane")
def step_open_preview_pane(context: Context) -> None:
    """Open the preview pane in the Wagtail admin."""
    context.page.get_by_role("button", name="Toggle preview").click()
    iframe = context.page.frame_locator("#w-preview-iframe")
    expect(iframe.get_by_text("Test Info Page", exact=True)).to_be_visible()


@then("session management should not be initialised in the iframe")
def step_session_not_initialised_in_iframe(context: Context) -> None:
    """Ensure session management only initialises once (in the parent), and not inside the iframe."""
    context.session_init_logs = []
    context.page.on(
        "console",
        lambda msg: (
            context.session_init_logs.append(msg.text)
            if "Initialising session management with config" in (msg.text or "")
            else None
        ),
    )

    context.execute_steps("""
        When the user clicks the "Save Draft" button
    """)

    # small pause for any stray logs
    context.page.wait_for_timeout(1000)

    # now assert we only saw one init-log total
    count = len(context.session_init_logs)
    assert count == 1, (
        f'Expected exactly one console message "Initialising session management with config" (in parent only), '
        f"but found {count}: {context.session_init_logs}"
    )
