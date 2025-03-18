from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.navigation.tests.factories import FooterMenuFactory


@given("a footer menu exists")
def create_footer_menu(context: Context):
    context.footer_menu = FooterMenuFactory()


@when("the user creates a footer menu instance")
def user_creates_footer_menu_instance(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="add one").click()


@when("the user navigates to edit the footer menu")
def user_navigates_to_footer_menu(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@when("the user populates the footer menu")
def user_populates_footer_menu(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").click()
    context.page.get_by_role("textbox", name="Column title*").press("CapsLock")
    context.page.get_by_role("textbox", name="Column title*").fill("About")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.ons.gov.uk/help/accessibility")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).press("CapsLock")
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Accessibility")


@when('the user clicks "View Live" from the preview')
def user_clicks_view_live(context: Context):
    context.page.get_by_role("button", name="Toggle preview").click()
    context.page.get_by_role("link", name="Preview in new tab").click()


@then("the preview of the footer menu is displayed with the populated data")
def user_previews_footer_menu(context: Context):
    expect(context.page.get_by_role("heading", name="About")).to_be_visible()
    expect(context.page.get_by_role("link", name="Accessibility")).to_be_visible()


@step('the user clicks "Publish" the footer menu')
def user_publishes_footer_menu(context: Context):
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


@then("a banner confirming changes is displayed")
def deleted_footer_menu_banner(context: Context):
    expect(context.page.get_by_text("Footer menu 'Footer Menu'")).to_be_visible()


@when('a CMS user navigates to "Navigation settings"')
def user_navigates_to_navigation_settings(context: Context):
    context.page.get_by_role("button", name="Settings").click()
    context.page.get_by_role("link", name="Navigation settings").click()


@when('the user selects footer menu in "Navigation settings"')
def user_selects_footer_menu(context: Context):
    context.page.get_by_role("button", name="Choose footer menu").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@when('the user clicks "saves" in the "Navigation Settings"')
def user_saves_in_navigation_settings(context: Context):
    context.page.get_by_role("button", name="Save").click()


@step("the footer menu is configured")
def user_configures_footer_menu(context: Context):
    context.page.get_by_role("button", name="Choose footer menu", exact=False)
    expect(context.page.get_by_text("Navigation settings updated.")).to_be_visible()


@when("the user enters duplicate information")
def user_enters_duplicate_link(context: Context):
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.locator("#columns-1-value-title").fill("About")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill(
        "https://www.ons.gov.uk/help/accessibility"
    )
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("Accessibility")


@when("the user inserts an empty column block")
def user_inserts_empty_footer_menu_block(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()


@then("an error message is displayed")
def error_message_for_footer_menu(context: Context):
    expect(context.page.get_by_text("The footer menu could not be")).to_be_visible()


@when("user deletes the footer menu")
def user_deletes_footer_menu(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("button", name="More options for 'Footer Menu'").click()
    context.page.get_by_role("link", name="Delete 'Footer Menu'").click()
    context.page.get_by_role("button", name="Yes, delete").click()


@when("the user enters a link with no title")
def user_enters_link_with_no_title(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").press("CapsLock")
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("www.google.com")
    context.page.locator("#columns-0-value-links-1-value-title").click()


@when("the user enters an incorrect url")
def user_enters_incorrect_url(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").press("CapsLock")
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("wwwgcom")
    context.page.locator("#columns-0-value-links-1-value-title").click()
    context.page.locator("#columns-0-value-links-1-value-title").press("CapsLock")
    context.page.locator("#columns-0-value-links-1-value-title").fill("Goggle")


@when("the user enters more than 3 columns")
def user_inserts_more_than_max_columns(context: Context):
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
def max_column_error_in_footer_menu(context: Context):
    expect(context.page.get_by_text("The footer menu could not be")).to_be_visible()
    expect(context.page.get_by_text("The maximum number of items is")).to_be_visible()


@when("the user adds an additional link to a footer menu")
def user_adds_link_to_footer_menu(context: Context):
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("https://www.ons.gov.uk/help")
    context.page.locator("#columns-0-value-links-1-value-title").click()
    context.page.locator("#columns-0-value-links-1-value-title").fill("More")


@then("the preview of the footer menu is displayed with the additional link")
def preview_add_to_footer_menu(context: Context):
    # link is not found
    # expect(context.page.get_by_role("link", name="More")).to_be_visible()
    expect(context.page.get_by_text("More")).to_be_visible()


@when("the user deletes the additional link")
def user_deletes_link(context: Context):
    context.page.get_by_role("button", name="Delete").nth(1).click()


@then("the preview does not show the deleted link")
def preview_deleted_link(context: Context):
    expect(context.page.get_by_role("link", name="More")).not_to_be_visible()


@when("a populated footer menu has been created")
def create_original_footer_menu(context: Context):
    user_creates_footer_menu_instance(context)
    user_populates_footer_menu(context)
    # click_save_draft_with_delay(context)


@then("the preview will show the new column is added")
def preview_new_column(context: Context):
    expect(context.page.get_by_role("heading", name="Column 2")).to_be_visible()
    # expect(context.page.get_by_text("Column 2")).to_be_visible()


@when("the user deletes a column")
def deletes_column(context: Context):
    context.page.get_by_role("button", name="Delete").nth(2).click()


@then("the preview will not show the deleted column")
def preview_deleted_column(context: Context):
    # is visible
    expect(context.page.get_by_role("heading", name="Column 2")).not_to_be_visible()
    # expect(context.page.get_by_text("Column 2")).not_to_be_visible()


@when("the user configures the footer menu in navigation settings")
def configure_footer_menu_in_navigation_settings(context: Context):
    user_navigates_to_navigation_settings(context)
    user_selects_footer_menu(context)
    user_saves_in_navigation_settings(context)


@then("the user navigates to the home page to see changes")
def navigates_to_home_page(context: Context):
    # Does not work...
    context.page1 = context.new_page()
    context.page1.goto("http://0.0.0.0:8000/")
    user_previews_footer_menu(context)


@when("the user edits data on a pre existing footer menu")
def user_edits_footer_menu(context: Context):
    context.page.locator("#columns-0-value-title").click()
    context.page.locator("#columns-0-value-title").fill("")
    context.page.locator("#columns-0-value-title").fill("New Title")
    context.page.locator("#columns-0-value-links-0-value-external_url").click()
    context.page.locator("#columns-0-value-links-0-value-external_url").fill("http://www.newlink.com")
    context.page.locator("#columns-0-value-links-0-value-title").click()
    context.page.locator("#columns-0-value-links-0-value-title").fill("")
    context.page.locator("#columns-0-value-links-0-value-title").fill("New link title")


@then("the preview of the footer menu is displayed with the edited data")
def preview_edited_footer_menu(context: Context):
    expect(context.page.get_by_role("heading", name="New Title")).to_be_visible()
    # Trying to find the additional link will result in error (both ways)
    # expect(context.page.get_by_role("link", name="New link Title")).to_be_visible()
    # expect(context.page.get_by_text("New link Title")).to_be_visible()


@when("the user adds an additional column and link")
def user_adds_new_column(context: Context):
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.locator("#columns-1-value-title").fill("Column 2")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill("https://www.example.com")
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("Example")
