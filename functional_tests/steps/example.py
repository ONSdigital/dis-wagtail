from behave import then, when
from behave.runner import Context
from behave_django.decorators import fixtures
from playwright.sync_api import expect

BASE_URL = "http://localhost:18000"
USERNAME = "test_editor"
PASSWORD = "test_editor"  # pragma: allowlist secret # noqa S105


@when("An external user navigates to the ONS beta site")  # pylint: disable=E1102
def external_user_navigates_to_beta_homepage(context: Context) -> None:
    """Navigates to the ONS beta site."""
    context.page.goto(BASE_URL)


@then("they can see the beta homepage")  # pylint: disable=E1102
def user_sees_the_beta_homepage(context: Context) -> None:
    """User sees the beta homepage."""
    expect(context.page.get_by_role("heading", name="Welcome to the ONS Wagtail")).to_be_visible()
    expect(context.page.get_by_label("Office for National Statistics homepage")).to_be_visible()
    expect(context.page.get_by_text("Home", exact=True)).to_be_visible()
    expect(context.page.get_by_text("This is a new service.")).to_be_visible()
    expect(context.page.get_by_text("Beta")).to_be_visible()


@fixtures("users.yml")
@when("An unauthenticated ONS CMS editor navigates to the beta CMS admin page")  # pylint: disable=E1102
def cms_admin_navigates_to_beta_homepage(context: Context) -> None:
    """Navigate to admin login page."""
    context.page.goto(f"{BASE_URL}/admin/login")


@when("they enter a their valid username and password and click login")  # pylint: disable=E1102
def enter_a_valid_username_and_password_and_sign_in(context: Context) -> None:
    """Enter the username and password and click login."""
    expect(context.page).to_have_url(f"{BASE_URL}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(USERNAME)
    context.page.get_by_placeholder("Enter password").fill(PASSWORD)
    context.page.get_by_role("button", name="Sign in").click()


@then("they are taken to the CMS admin homepage")  # pylint: disable=E1102
def user_sees_admin_homepage(context: Context) -> None:
    """Verify we arrive authenticated on the admin dashboard."""
    expect(context.page).to_have_url(f"{BASE_URL}/admin/")
    expect(context.page.get_by_role("heading", name="Office For National Statistics")).to_be_visible()
    expect(context.page.get_by_label("Dashboard")).to_be_visible()
    expect(context.page.get_by_role("button", "pages")).to_be_visible()
    expect(context.page).to_have_url(f"http://{BASE_URL}/admin/")
