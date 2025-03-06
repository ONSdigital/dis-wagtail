from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.navigation.tests.factories import FooterMenuFactory


@given("a footer menu exists")
def create_footer_menu(context: Context):
    context.footer_menu = FooterMenuFactory()


@when("the user creates a footer menu instance")
from cms.navigation.tests.factories import FooterMenuFactory


@given("footer menu exists")
def create_footer_menu(context: Context):
    context.footer_menu = FooterMenuFactory()


@when("the user creates a footer menu")
def user_creates_footer_menu(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="add one").click()


@when("the user navigates to edit the footer menu")
def user_click_footer(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click(timeout=5000)


@when("user clicks footer menu")
def user_click_footer(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click(timeout=5000)


@when("the user populates the footer menu")
def user_populates_footer_menu(context: Context):
    context.page.get_by_role("textbox", name="Column title*").click()
    context.page.get_by_role("textbox", name="Column title*").press("CapsLock")
    context.page.get_by_role("textbox", name="Column title*").fill("About")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.ons.gov.uk/help/accessibility")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).press("CapsLock")
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Accessibility")


@when("the user enters duplicate information")
def duplicate_info(context: Context):
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.locator("#columns-1-value-title").fill("About")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill(
        "https://www.ons.gov.uk/help/accessibility"
    )
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("Accessibility")


@when('the user clicks "View Live" from the preview')
def user_clicks_view_live(context: Context):
    context.page.get_by_role("button", name="Toggle preview").click()
    with context.page.expect_popup():
        context.page.get_by_role("link", name="Preview in new tab").click()


@then("the preview of the footer menu is displayed with the populated data")
def preview_footer_menu(context: Context):
    expect(context.page.get_by_role("heading", name="About")).to_be_visible()
    expect(context.page.get_by_role("link", name="Accessibility")).to_be_visible()


@when("the user inserts an empty column block")
def empty_footer_menu(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()


@then("an error message is displayed")
def error_message_footer_menu(context: Context):
    expect(context.page.get_by_text("The footer menu could not be")).to_be_visible()


@when('a CMS user navigates to "Navigation settings"')
def navigation_settings(context: Context):
    context.page.get_by_role("button", name="Settings").click()
    context.page.get_by_role("link", name="Navigation settings").click()


@when("the user selects footer menu")
def footer_menu_nav_set(context: Context):
    context.page.get_by_role("button", name="Choose footer menu").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@when('the user clicks "saves" in the Navigation Settings')
def click_save(context: Context):
    context.page.get_by_role("button", name="Save").click()


@step("the footer menu is configured")
def assign_footer_menu(context: Context):
    context.page.get_by_role("button", name="Choose footer menu", exact=False)
    expect(context.page.get_by_text("Navigation settings updated.")).to_be_visible()
    expect(context.page.get_by_text("Navigation settings updated.")).to_be_visible()


@when("user deletes the footer menu")
def deletes_footer_menu(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("button", name="More options for 'Footer Menu'").click()
    context.page.get_by_role("link", name="Delete 'Footer Menu'").click()
    context.page.get_by_role("button", name="Yes, delete").click()


@then("a banner confirming changes is displayed")
def deleted_footer(context: Context):
    expect(context.page.get_by_text("Footer menu 'Footer Menu'")).to_be_visible()


@step('the user clicks "Publish" the footer menu')
def publish_menu(context: Context):
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()
@when("the user edits a footer menu")
def edit_footer_menu(context: Context):
    context.page.get_by_role("textbox", name="Column title*").click()
    context.page.get_by_role("textbox", name="Column title*").fill("About")
    context.page.get_by_role("region", name="https://www.ons.gov.uk/help/").get_by_label("Title").click()
    context.page.get_by_role("region", name="https://www.ons.gov.uk/help/").get_by_label("Title").fill("Accessibility")


@then("menu is published")
def confirm_publish(context: Context):
    expect(context.page.get_by_text("updated and published")).to_be_visible()


@when("the user enters a link with no title")
def link_no_title(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").press("CapsLock")
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("www.google.com")
    context.page.locator("#columns-0-value-links-1-value-title").click()


@when("the user enters an incorrect url")
def incorrect_url(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").press("CapsLock")
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("wwwgcom")
    context.page.locator("#columns-0-value-links-1-value-title").click()
    context.page.locator("#columns-0-value-links-1-value-title").press("CapsLock")
    context.page.locator("#columns-0-value-links-1-value-title").fill("Goggle")


@when("the user enters more than 3 columns")
def more_than_max_column(context: Context):
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.locator("#columns-1-value-title").click()
    context.page.locator("#columns-1-value-title").fill("Title 2")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill("2nd link")
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("2nd link title")
    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.locator("#columns-2-value-title").click()
    context.page.locator("#columns-2-value-title").fill("Title 3")
    context.page.locator("#columns-2-value-links-0-value-external_url").click()
    context.page.locator("#columns-2-value-links-0-value-external_url").fill("3rd link")
    context.page.locator("#columns-2-value-links-0-value-title").click()
    context.page.locator("#columns-2-value-links-0-value-title").fill("3rd link title")
    context.page.get_by_role("button", name="Insert a block").nth(3).click()
    context.page.locator("#columns-3-value-title").fill("Title 4")
    context.page.locator("#columns-3-value-links-0-value-external_url").click()
    context.page.locator("#columns-3-value-links-0-value-external_url").fill("4th link")
    context.page.locator("#columns-3-value-links-0-value-title").click()
    context.page.locator("#columns-3-value-links-0-value-title").fill("4th link title")


@then("an error message and maximum number of column notification is displayed")
def max_column_error(context: Context):
    expect(context.page.get_by_text("The footer menu could not be")).to_be_visible()
    expect(context.page.get_by_text("The maximum number of items is")).to_be_visible()


@when("the user adds an additional link to a footer menu")
def user_edit_footer(context: Context):
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.locator("#columns-1-value-title").fill("More")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill("https://www.ons.gov.uk/help")
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("Help")


@then("the preview of the footer menu is displayed with the added data")
def preview_edit_footer_menu(context: Context):
    expect(context.page.get_by_role("heading", name="More")).to_be_visible()
@when("the preview of the footer menu is displayed with the edited data")
def edited_footer_menu(context: Context):
    expect(context.page.get_by_role("link", name="Site")).to_be_visible()
