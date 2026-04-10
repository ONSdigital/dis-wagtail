# pylint: disable=not-callable

from behave import then, when
from behave.runner import Context
from playwright.sync_api import expect


@when("the user opens the account details page")
def user_opens_account_details_page(context: Context) -> None:
    """Navigate to the account details page."""
    context.page.goto(f"{context.base_url}/admin/account/")


@then("they can see their account details")
def user_sees_account_details(context: Context) -> None:
    """Assert the account details are visible."""
    expect(context.page.get_by_role("heading", name="Name and Email")).to_be_visible()

    expect(context.page.get_by_role("textbox", name="First Name")).to_have_value(context.user_data["user"].first_name)
    expect(context.page.get_by_role("textbox", name="Last Name")).to_have_value(context.user_data["user"].last_name)
    expect(context.page.get_by_role("textbox", name="Email")).to_have_value(context.user_data["user"].email)


@then("they cannot edit their first name, last name or email")
def user_cannot_edit_account_details(context: Context) -> None:
    """Assert the account details fields are disabled."""
    expect(context.page.get_by_role("textbox", name="First Name")).to_be_disabled()
    expect(context.page.get_by_role("textbox", name="Last Name")).to_be_disabled()
    expect(context.page.get_by_role("textbox", name="Email")).to_be_disabled()


@when('the user changes their theme to "Dark"')
def user_changes_theme(context: Context) -> None:
    """Select a theme and save the form."""
    context.page.get_by_label("Admin theme").select_option(label="Dark")


@when('the user clicks "Save" to save the account details')
def user_saves_account_details(context: Context) -> None:
    """Click the save button to save the account details form."""
    context.page.get_by_role("button", name="Save").click()


@then('the user\'s theme is updated to "Dark"')
def user_theme_is_updated(context: Context) -> None:
    """Assert the theme select shows the chosen value."""
    expect(context.page.get_by_label("Admin theme")).to_have_value("dark")


@when("the user clicks on the Notifications tab")
def user_clicks_notifications_tab(context: Context) -> None:
    """Click the Notifications tab."""
    context.page.get_by_role("tab", name="Notifications").click()


@when("the user toggles Submitted notifications on")
def user_toggles_submitted_notifications(context: Context) -> None:
    """Check the Submitted notifications checkbox."""
    context.page.get_by_label("Submitted notifications").check(force=True)


@then("the user's Submitted notifications setting is updated to on")
def user_submitted_notifications_is_on(context: Context) -> None:
    """Assert the Submitted notifications checkbox is checked after saving."""
    context.page.get_by_role("tab", name="Notifications").click()
    expect(context.page.get_by_label("Submitted notifications")).to_be_checked()
