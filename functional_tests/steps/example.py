from behave import given, then, when
from behave.runner import Context
from playwright.sync_api import expect

# TODO pylint gets a false E1102 on all behave fixture annotations, find a better way to ignore  pylint: disable=W0511


@when("An external user navigates to the ONS beta site")  # pylint: disable=E1102
def external_user_navigates_to_beta_homepage(context: Context) -> None:
    """Navigates to the ONS beta site."""
    context.page.goto(context.base_url)


@then("they can see the beta homepage")  # pylint: disable=E1102
def user_sees_the_beta_homepage(context: Context) -> None:
    """User sees the beta homepage."""
    expect(context.page.get_by_role("heading", name="Welcome to the ONS Wagtail")).to_be_visible()
    expect(context.page.get_by_label("Office for National Statistics homepage")).to_be_visible()
    expect(context.page.get_by_text("Home", exact=True)).to_be_visible()
    expect(context.page.get_by_text("This is a new service.")).to_be_visible()
    expect(context.page.get_by_text("Beta")).to_be_visible()


@given("the user is a CMS admin")  # pylint: disable=E1102
def user_is_cms_admin(context: Context) -> None:
    """Create an admin user."""
    # TODO this import fails at the top level with error:  pylint: disable=W0511
    #  "django.core.exceptions.AppRegistryNotReady: Models aren't loaded yet."
    #   Find a better solution
    from functional_tests.factories import DEFAULT_TEST_PASSWORD, UserFactory  # pylint: disable=C0415

    user = UserFactory()
    context.username = user.username
    context.password = DEFAULT_TEST_PASSWORD


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


@given("the user logs into the CMS admin site")  # pylint: disable=E1102
def user_logs_into_admin_site(context: Context) -> None:
    """Log into admin site."""
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.username)
    context.page.get_by_placeholder("Enter password").fill(context.password)
    context.page.get_by_role("button", name="Sign in").click()
    expect(context.page).to_have_url(f"{context.base_url}/admin/")


@when("the user navigates to the home page and clicks create new page")  # pylint: disable=E1102
def create_new_page_under_home(context: Context) -> None:
    """Create a new page under home."""
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home", exact=True).click()
    context.page.get_by_label("Add child page").click()


@when("they enter some example page information")  # pylint: disable=E1102
def enter_example_page_information(context: Context) -> None:
    """Enter some example page information."""
    context.page.get_by_placeholder("Page title*").fill("Test Example")
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.locator(".public-DraftStyleDefault-block").click()
    context.page.get_by_role("textbox").nth(2).fill("WARNING, THIS IS A TEST")
    context.page.get_by_role("textbox").nth(2).press("Tab")
    context.page.get_by_label("Title (optional)").fill("WARNING")


@when("they click Publish")  # pylint: disable=E1102
def publish_page(context: Context) -> None:
    """Click Publish button."""
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


@then("the new Example page is visible on the website")  # pylint: disable=E1102
def new_example_page_is_visible(context: Context) -> None:
    """Check new example page is visible on the website."""
    context.page.get_by_text("Page 'Test Example' created and published. View live Edit Exploring: Home Root").click()
    with context.page.expect_popup() as page1_info:
        context.page.get_by_role("link", name="Current page status: live").first.click()
    live_example_page = page1_info.value
    expect(live_example_page.get_by_role("banner").get_by_text("Test Example")).to_be_visible()
    expect(live_example_page.get_by_role("banner").get_by_text("Test Example")).to_be_visible()
    expect(live_example_page.get_by_text("WARNING, THIS IS A TEST")).to_be_visible()
