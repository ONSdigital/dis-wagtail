# pylint: disable=not-callable
from behave import then, when
from behave.runner import Context
from playwright.sync_api import expect


@when("An external user navigates to the ONS beta site homepage")
def external_user_navigates_to_beta_homepage(context: Context) -> None:
    context.page.goto(context.base_url)


@when("the user clicks on the Wagtail Core Default Login link")
def user_clicks_wagtail_core_login_link(context: Context) -> None:
    context.page.get_by_role("button", name="Wagtail Core Default Login").click()


@then("they can see the beta homepage")
def user_sees_the_beta_homepage(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Home")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Welcome to the ONS Wagtail")).to_be_visible()
    # The ONS logo will appear twice, once for mobile and once for desktop
    expect(context.page.get_by_label("Office for National Statistics logo")).to_have_count(2)
    # The desktop logo should be visible
    expect(context.page.get_by_label("Office for National Statistics logo").nth(0)).to_be_visible()
    expect(context.page.get_by_text("This is a new service.")).to_be_visible()
    expect(context.page.get_by_text("Beta")).to_be_visible()


@then("they are redirected to the Wagtail admin login page")
def user_redirected_to_wagtail_admin_login_page(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Sign in to Wagtail")).to_be_visible()
    expect(context.page.get_by_label("Username")).to_be_visible()
    expect(context.page.get_by_label("Password")).to_be_visible()
    expect(context.page.get_by_role("button", name="Sign in")).to_be_visible()


@when("the user navigates to the English home page in the Wagtail page explorer")
def navigate_to_english_home_page_in_page_explorer(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home English").click()
