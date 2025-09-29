import json
from collections.abc import Iterable

from behave import given, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@given("the browsers cookies are cleared")
def clear_browser_cookies(context: Context) -> None:
    context.page.context.clear_cookies()


@when('the user is clicks "Accept additional cookies" on the cookies banner')
def user_accepts_additional_cookies_in_banner(context: Context) -> None:
    context.page.get_by_role("button", name="Accept additional cookies").click()


@when('the user is clicks "Reject additional cookies" on the cookies banner')
def user_rejects_additional_cookies_in_banner(context: Context) -> None:
    context.page.get_by_role("button", name="Reject additional cookies").click()


@when("the cookies banner is displayed")
def check_cookies_banner_is_displayed(context: Context) -> None:
    expect(context.page.get_by_role("region", name="Cookies banner")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Cookies on ons.gov.uk")).to_be_visible()
    expect(context.page.get_by_role("button", name="Accept additional cookies")).to_be_visible()
    expect(context.page.get_by_role("button", name="Reject additional cookies")).to_be_visible()
    expect(context.page.get_by_role("link", name="additional cookies")).to_be_visible()
    expect(context.page.get_by_role("link", name="View cookies")).to_be_visible()


@when('the user clicks "View cookies" on the cookies banner')
def user_clicks_view_cookies_in_banner(context: Context) -> None:
    context.page.get_by_role("link", name="View cookies").click()


@when("the user is taken to the cookies management page")
def check_user_is_on_cookies_management_page(context: Context) -> None:
    expect(context.page).to_have_url(f"{context.base_url}/cookies")
    expect(context.page.get_by_role("heading", name="Cookies on ONS.GOV.UK", exact=True)).to_be_visible()
    expect(context.page.get_by_role("heading", name="Cookie settings")).to_be_visible()


@then("all the optional cookies are disabled in the browser")
def check_all_optional_cookies_are_disabled(context: Context) -> None:
    cookies = context.page.context.cookies(urls=[context.base_url])
    check_ons_cookie_policy_values(
        cookies,
        {
            "essential": True,
            "campaigns": False,
            "usage": False,
            "settings": False,
        },
    )


@then("all the optional cookies are enabled in the browser")
def check_all_optional_cookies_are_set_in_browser(context: Context) -> None:
    cookies = context.page.context.cookies(urls=[context.base_url])
    check_ons_cookie_policy_values(
        cookies,
        {
            "essential": True,
            "campaigns": True,
            "usage": True,
            "settings": True,
        },
    )


@when("the user turns on only the {cookie_type} cookies")
def user_turns_on_only_cookie_type_cookies(context: Context, cookie_type: str) -> None:
    cookie_type_radio_locator = {
        "usage": "Do you want to allow usage tracking?",
        "campaigns": "Do you want to allow third party usage tracking?",
        "settings": "Do you want to allow cookies for potential future use that tailor your experience?",
    }

    context.page.get_by_role("group", name=cookie_type_radio_locator[cookie_type]).get_by_label("On").check()


@when('the user clicks "Save settings"')
def user_saves_cookie_settings(context: Context) -> None:
    context.page.get_by_role("button", name="Save changes").click()


@then("a confirmation message is displayed")
def the_user_sees_confirmation_message(context: Context) -> None:
    expect(context.page.get_by_role("alert", name="Completed:")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Your cookie settings have been saved")).to_be_visible()


@then("only the {cookie_type} cookies are enabled in the browser")
def check_only_cookie_type_cookies_are_enabled_in_browser(context: Context, cookie_type: str) -> None:
    cookies = context.page.context.cookies(urls=[context.base_url])
    expected_values = {"essential": True, "campaigns": False, "usage": False, "settings": False, cookie_type: True}
    check_ons_cookie_policy_values(cookies, expected_values)


def check_ons_cookie_policy_values(cookies: Iterable[dict], expected_values: dict[str, bool]) -> None:
    policy_cookies = list(filter(lambda cookie: cookie["name"] == "ons_cookie_policy", cookies))
    assert len(policy_cookies) == 1, "There must be exactly one ons_cookie_policy cookie set"

    cookie_policy_cookie = policy_cookies[0]
    cookie_policy_values_raw = cookie_policy_cookie["value"]
    cookie_policy_values = json.loads(cookie_policy_values_raw.replace("'", '"'))
    for value_name, expected_value in expected_values.items():
        assert cookie_policy_values.get(value_name) is expected_value, (
            f'Value of "{value_name}" must be set to {expected_value} in ons_cookie_policy cookie, '
            f"but was {cookie_policy_values.get(value_name)}"
        )
