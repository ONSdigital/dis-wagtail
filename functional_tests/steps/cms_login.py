# pylint: disable=not-callable
from behave import given, step, then, when
from behave.runner import Context
from playwright.sync_api import expect

from functional_tests.step_helpers.users import create_user, get_user_data
from functional_tests.steps.auth import step_click_logout


@given("the user is a CMS admin")
def user_is_cms_admin(context: Context) -> None:
    context.user_data = create_user(user_type="superuser")


@when("the user opens the beta CMS admin page")
def cms_admin_navigates_to_beta_homepage(context: Context) -> None:
    context.page.goto(f"{context.base_url}/admin/login/")


@when("they enter a their valid username and password and click login")
def enter_a_valid_username_and_password_and_sign_in(context: Context) -> None:
    context.page.get_by_placeholder("Enter your username").fill(context.user_data["username"])
    context.page.get_by_placeholder("Enter password").fill(context.user_data["password"])
    context.page.get_by_role("button", name="Sign in").click()


@then("they are taken to the CMS admin homepage")
def user_sees_admin_homepage(context: Context) -> None:
    expect(context.page).to_have_url(f"{context.base_url}/admin/")
    expect(context.page.get_by_role("heading", name="Office For National Statistics")).to_be_visible()
    expect(context.page.get_by_label("Dashboard")).to_be_visible()


@step("the user is logged in")
def the_user_logs_in(context: Context) -> None:
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.user_data["username"])
    context.page.get_by_placeholder("Enter password").fill(context.user_data["password"])
    context.page.get_by_role("button", name="Sign in").click()


@step("a {user_type} logs into the admin site")
def a_user_logs_in(context: Context, user_type: str) -> None:
    context_attr = user_type.lower().replace(" ", "_")
    if user := getattr(context, context_attr, None):
        context.user_data = get_user_data(user)
    else:
        context.user_data = create_user(user_type)
        setattr(context, context_attr, context.user_data["user"])
    the_user_logs_in(context)


@step("a {user_type} is logged in")
def a_user_is_logged_in(context: Context, user_type: str) -> None:
    step_click_logout(context)
    a_user_logs_in(context, user_type)
