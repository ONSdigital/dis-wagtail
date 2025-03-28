from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.navigation.tests.factories import FooterMenuFactory


@given("a footer menu exists")
def create_footer_menu(context: Context):
    context.footer_menu = FooterMenuFactory()


@step("the user creates a footer menu instance")
def user_creates_footer_menu_instance(context: Context):
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Add footer menu").click()


@when("the user populates the footer menu with a page")
def user_populates_footer_menu_with_page(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").fill("Home page")
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("link", name="Home").click()


@then("the footer menu is displayed on the preview pane")
def footer_menu_preview_pane(context: Context):
    iframe_locator = context.page.frame_locator("#w-preview-iframe")
    expect(iframe_locator.get_by_role("link", name="Home")).to_be_visible()


@step("the user populates the footer menu")
def user_populates_footer_menu(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").click()
    context.page.get_by_role("textbox", name="Column title*").fill("Link Column 1")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.link-column-1.com/")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Link Title 1")


@step("a banner confirming the deletion is displayed")
@then("a banner confirming changes is displayed")
def footer_menu_banner_confirmation(context: Context):
    expect(context.page.get_by_text("Footer menu 'Footer Menu'")).to_be_visible()


@when("the user navigates to navigation settings")
def user_navigates_to_navigation_settings(context: Context):
    context.page.get_by_role("button", name="Settings").click()
    context.page.get_by_role("link", name="Navigation settings").click()


@when("the user selects the footer menu")
def user_selects_footer_menu(context: Context):
    context.page.get_by_role("button", name="Choose footer menu").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@step("the footer menu is configured successfully")
def user_configures_footer_menu(context: Context):
    expect(context.page.get_by_text("Navigation settings updated.")).to_be_visible()


@when("the user inserts an empty column block")
def user_inserts_empty_footer_menu_block(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()


@then("an error message is displayed preventing saving an empty column block")
def empty_column_error(context: Context):
    expect(context.page.get_by_text("This field is required.")).to_be_visible()
    context.page.get_by_text("Missing required fields").click()
    context.page.locator("#columns-0-value-links-0-value-page-errors").get_by_text(
        "Either Page or External Link"
    ).click()
    context.page.locator("#columns-0-value-links-0-value-external_url-errors").get_by_text(
        "Either Page or External Link"
    ).click()


@then("the preview of the footer menu is displayed with the populated data")
def user_previews_footer_menu(context: Context):
    # Heading and link
    expect(context.page.get_by_role("heading", name="About")).to_be_visible()
    expect(context.page.get_by_role("link", name="Accessibility")).to_be_visible()


@when("the user populates the footer menu with duplicate links")
def user_enters_duplicate_link(context: Context):
    user_populates_footer_menu(context)
    context.page.get_by_role("button", name="Add").nth(1).click()
    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("https://www.link-column-1.com/")
    context.page.locator("#columns-0-value-links-1-value-title").click()
    context.page.locator("#columns-0-value-links-1-value-title").fill("Link Title 2")


@then("an error message is displayed for duplicate links")
def duplicate_link_error(context: Context):
    expect(context.page.locator("#columns-0-value-links-1-value-external_url-errors")).to_contain_text(
        "Duplicate URL. Please add a different one."
    )


@when("the user adds a link with no title")
def user_enters_link_with_no_title(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").fill("Link Column 1")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.link-column-1.com/")


@then("an error message is displayed about the missing title")
def missing_title_error(context: Context):
    expect(context.page.locator("#columns-0-value-links-0-value-title-errors")).to_contain_text(
        "Title is required for external links."
    )


@when("the user adds a malformed URL")
def user_enters_incorrect_url(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").fill("Link Column 1")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("htp:/malformed-url")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Malformed URL")


@then("an error message is displayed about the URL format")
def url_format_error(context: Context):
    expect(context.page.locator("#columns-0-value-links-0-value-external_url-errors")).to_contain_text(
        "Enter a valid URL."
    )


@when("the user adds more than 3 columns")
def user_inserts_more_than_max_columns(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").fill("Link Column 1")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.link-column-1.com/")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Link Title 1")
    context.page.get_by_role("button", name="Insert a block").nth(1).click()

    context.page.locator("#columns-1-value-title").fill("Link Column 2")
    context.page.locator("#columns-1-value-links-0-value-external_url").click()
    context.page.locator("#columns-1-value-links-0-value-external_url").fill("https://www.link-column-2.com/")
    context.page.locator("#columns-1-value-links-0-value-title").click()
    context.page.locator("#columns-1-value-links-0-value-title").fill("Link Title 2")
    context.page.get_by_role("button", name="Insert a block").nth(2).click()

    context.page.locator("#columns-2-value-title").fill("Link Column 3")
    context.page.locator("#columns-2-value-links-0-value-external_url").click()
    context.page.locator("#columns-2-value-links-0-value-external_url").fill("https://www.link-column-3.com/")
    context.page.locator("#columns-2-value-links-0-value-title").click()
    context.page.locator("#columns-2-value-links-0-value-title").fill("Link Title 3")
    context.page.get_by_role("button", name="Insert a block").nth(3).click()

    context.page.locator("#columns-3-value-title").fill("Link Column 4")
    context.page.locator("#columns-3-value-links-0-value-external_url").click()
    context.page.locator("#columns-3-value-links-0-value-external_url").fill("https://www.link-column-4.com/")
    context.page.locator("#columns-3-value-links-0-value-title").click()
    context.page.locator("#columns-3-value-links-0-value-title").fill("Link Title 4")


@then("an error message is displayed about column limit")
def max_column_error(context: Context):
    expect(context.page.locator("#panel-columns-content")).to_contain_text("The maximum number of items is 3")


@when("the user adds more than 10 links")
def user_adds_above_max_links(context: Context):
    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("textbox", name="Column title*").fill("Link Column 1")
    context.page.get_by_role("textbox", name="or External Link").click()
    context.page.get_by_role("textbox", name="or External Link").fill("https://www.link-column-1-link-0.com/")
    context.page.get_by_role("textbox", name="Title", exact=True).click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Link Title 1")
    context.page.get_by_role("button", name="Add").nth(1).click()

    context.page.locator("#columns-0-value-links-1-value-external_url").click()
    context.page.locator("#columns-0-value-links-1-value-external_url").fill("https://www.link-column-1-link-1.com/")
    context.page.locator("#columns-0-value-links-1-value-title").click()
    context.page.locator("#columns-0-value-links-1-value-title").fill("Link Title 2")
    context.page.get_by_role("button", name="Add").nth(2).click()

    context.page.locator("#columns-0-value-links-2-value-external_url").click()
    context.page.locator("#columns-0-value-links-2-value-external_url").fill("https://www.link-column-1-link-2.com/")
    context.page.locator("#columns-0-value-links-2-value-title").click()
    context.page.locator("#columns-0-value-links-2-value-title").fill("Link Title 3")
    context.page.get_by_role("button", name="Add").nth(3).click()

    context.page.locator("#columns-0-value-links-3-value-external_url").click()
    context.page.locator("#columns-0-value-links-3-value-external_url").fill("https://www.link-column-1-link-3.com/")
    context.page.locator("#columns-0-value-links-3-value-title").click()
    context.page.locator("#columns-0-value-links-3-value-title").fill("Link Title 4")
    context.page.get_by_role("button", name="Add").nth(4).click()

    context.page.locator("#columns-0-value-links-4-value-external_url").click()
    context.page.locator("#columns-0-value-links-4-value-external_url").fill("https://www.link-column-1-link-4.com/")
    context.page.locator("#columns-0-value-links-4-value-title").click()
    context.page.locator("#columns-0-value-links-4-value-title").fill("Link Title 5")
    context.page.get_by_role("button", name="Add").nth(5).click()

    context.page.locator("#columns-0-value-links-5-value-external_url").click()
    context.page.locator("#columns-0-value-links-5-value-external_url").fill("https://www.link-column-1-link-5.com/")
    context.page.locator("#columns-0-value-links-5-value-title").click()
    context.page.locator("#columns-0-value-links-5-value-title").fill("Link Title 6")
    context.page.get_by_role("button", name="Add").nth(6).click()

    context.page.locator("#columns-0-value-links-6-value-external_url").click()
    context.page.locator("#columns-0-value-links-6-value-external_url").fill("https://www.link-column-1-link-6.com/")
    context.page.locator("#columns-0-value-links-6-value-title").click()
    context.page.locator("#columns-0-value-links-6-value-title").fill("Link Title 7")
    context.page.get_by_role("button", name="Add").nth(7).click()

    context.page.locator("#columns-0-value-links-7-value-external_url").click()
    context.page.locator("#columns-0-value-links-7-value-external_url").fill("https://www.link-column-1-link-7.com/")
    context.page.locator("#columns-0-value-links-7-value-title").click()
    context.page.locator("#columns-0-value-links-7-value-title").fill("Link Title 8")
    context.page.get_by_role("button", name="Add").nth(8).click()

    context.page.locator("#columns-0-value-links-8-value-external_url").click()
    context.page.locator("#columns-0-value-links-8-value-external_url").fill("https://www.link-column-1-link-8.com/")
    context.page.locator("#columns-0-value-links-8-value-title").click()
    context.page.locator("#columns-0-value-links-8-value-title").fill("Link Title 9")
    context.page.get_by_role("button", name="Add").nth(9).click()

    context.page.locator("#columns-0-value-links-9-value-external_url").click()
    context.page.locator("#columns-0-value-links-9-value-external_url").fill("https://www.link-column-1-link-9.com/")
    context.page.locator("#columns-0-value-links-9-value-title").click()
    context.page.locator("#columns-0-value-links-9-value-title").fill("Link Title 10")
    context.page.get_by_role("button", name="Add").nth(10).click()

    context.page.locator("#columns-0-value-links-10-value-external_url").click()
    context.page.locator("#columns-0-value-links-10-value-external_url").fill("https://www.link-column-1-link-10.com/")
    context.page.locator("#columns-0-value-links-10-value-title").click()
    context.page.locator("#columns-0-value-links-10-value-title").fill("Link Title 11")


@then("an error message is displayed about the link limit")
def max_link_error(context: Context):
    expect(context.page.locator("#panel-columns-content")).to_contain_text("The maximum number of items is 10")
