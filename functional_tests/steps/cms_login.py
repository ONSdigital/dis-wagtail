from behave import given, then, when  # pylint: disable=E0611
from behave.runner import Context
from playwright.sync_api import expect


@given("the user is a CMS admin")  # pylint: disable=E1102
def user_is_cms_admin(context: Context) -> None:
    """Create an admin user."""
    context.username, context.password = create_cms_admin_user()


@when("the user navigates to the beta CMS admin page")  # pylint: disable=E1102
def cms_admin_navigates_to_beta_homepage(context: Context) -> None:
    """Navigate to admin login page."""
    context.page.goto(f"{context.base_url}/admin/login/")


@when("they enter a their valid username and password and click login")  # pylint: disable=E1102
def enter_a_valid_username_and_password_and_sign_in(context: Context) -> None:
    """Enter the username and password and click login."""
    expect(context.page).to_have_url(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.username)
    context.page.get_by_placeholder("Enter password").fill(context.password)
    context.page.get_by_role("button", name="Sign in").click()


@then("they are taken to the CMS admin homepage")  # pylint: disable=E1102
def user_sees_admin_homepage(context: Context) -> None:
    """Verify we arrive authenticated on the admin dashboard."""
    expect(context.page).to_have_url(f"{context.base_url}/admin/")
    expect(context.page.get_by_role("heading", name="Office For National Statistics")).to_be_visible()
    expect(context.page.get_by_label("Dashboard")).to_be_visible()


@given("a CMS user logs into the admin site")
def user_logs_into_the_admin_site(context: Context) -> None:
    """Creates a user and logs into the admin site."""
    context.username, context.password = create_cms_admin_user()
    context.page.goto(f"{context.base_url}/admin/login/")
    expect(context.page).to_have_url(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.username)
    context.page.get_by_placeholder("Enter password").fill(context.password)
    context.page.get_by_role("button", name="Sign in").click()


def create_cms_admin_user() -> tuple[str, str]:
    """Creates a CMS admin user using a factory, returns the username and password."""
    # TODO this import fails at the top level with error:  pylint: disable=W0511
    #  "django.core.exceptions.AppRegistryNotReady: Models aren't loaded yet."
    #   Find a better solution
    from functional_tests.factories import DEFAULT_TEST_PASSWORD, UserFactory  # pylint: disable=C0415

    user = UserFactory()
    return user.username, DEFAULT_TEST_PASSWORD
