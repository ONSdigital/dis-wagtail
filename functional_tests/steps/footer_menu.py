# pylint: disable=not-callable
from behave import given, step, then, when
from behave.runner import Context
from playwright.sync_api import expect

from cms.navigation.tests.factories import FooterMenuFactory
from functional_tests.step_helpers.footer_menu_helpers import (
    choose_page_link,
    fill_column_link,
    fill_column_title,
    generate_columns,
    insert_block,
)


@given("a footer menu exists")
def create_footer_menu(context: Context) -> None:
    context.footer_menu = FooterMenuFactory()


@step("the user creates a footer menu instance")
def user_creates_footer_menu_instance(context: Context) -> None:
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name="Footer menus").click()
    context.page.get_by_role("link", name="Add footer menu").click()


@when("the user populates the footer menu with an internal link")
def user_populates_footer_menu_with_page(context: Context) -> None:
    insert_block(context.page)
    context.page.get_by_role("textbox", name="Column title*").fill("Home page")
    choose_page_link(context.page, page_name="Home")


@then("the footer menu is displayed on the preview pane with an internal link")
def footer_menu_preview_pane(context: Context) -> None:
    iframe_locator = context.page.frame_locator("#w-preview-iframe")
    expect(iframe_locator.get_by_role("link", name="Home")).to_be_visible()


@step("the user populates the footer menu with an external link")
def user_populates_footer_menu(context: Context) -> None:
    insert_block(context.page)
    fill_column_title(context.page, col_index=0, title="Link Column 1")
    fill_column_link(
        context.page,
        col_index=0,
        link_index=0,
        external_url="https://www.link-column-1.com/",
        link_title="Link Title 1",
    )


@step("a banner confirming the deletion is displayed")
@then("a banner confirming changes is displayed")
def footer_menu_banner_confirmation(context: Context) -> None:
    expect(context.page.get_by_text("Footer menu 'Footer Menu'")).to_be_visible()


@then("the footer menu is displayed on the preview pane with an external link")
def populated_footer_menu_preview_pane(context: Context) -> None:
    iframe_locator = context.page.frame_locator("#w-preview-iframe")
    expect(iframe_locator.get_by_role("heading", name="Link Column 1")).to_be_visible()
    expect(iframe_locator.get_by_role("link", name="Link Title 1")).to_be_visible()


@when("the user navigates to navigation settings")
def user_navigates_to_navigation_settings(context: Context) -> None:
    context.page.get_by_role("button", name="Settings").click()
    context.page.get_by_role("link", name="Navigation settings").click()


@when("the user selects the footer menu")
def user_selects_footer_menu(context: Context) -> None:
    context.page.get_by_role("button", name="Choose footer menu").click()
    context.page.get_by_role("link", name="Footer Menu", exact=True).click()


@step("the footer menu is saved successfully")
def user_configures_footer_menu(context: Context) -> None:
    expect(context.page.get_by_text("Navigation settings updated.")).to_be_visible()


@when("the user inserts an empty column block")
def user_inserts_empty_footer_menu_block(context: Context) -> None:
    insert_block(context.page)


@then("an error message is displayed preventing saving an empty column block")
def empty_column_error(context: Context) -> None:
    expect(context.page.get_by_text("This field is required.")).to_be_visible()
    expect(context.page.get_by_text("Missing required fields")).to_be_visible()
    expect(context.page.locator("#columns-0-value-links-0-value-page-errors")).to_contain_text(
        "Either Page or External Link"
    )
    expect(context.page.locator("#columns-0-value-links-0-value-external_url-errors")).to_contain_text(
        "Either Page or External Link"
    )


@when("the user populates the footer menu with duplicate links")
def user_enters_duplicate_link(context: Context) -> None:
    user_populates_footer_menu(context)
    fill_column_link(
        context.page,
        col_index=0,
        link_index=1,
        external_url="https://www.link-column-1.com/",
        link_title="Link Title 2",
    )


@then("an error message is displayed for duplicate links")
def duplicate_link_error(context: Context) -> None:
    expect(context.page.locator("#columns-0-value-links-1-value-external_url-errors")).to_contain_text(
        "Duplicate URL. Please add a different one."
    )


@when("the user adds a link with no title")
def user_enters_link_with_no_title(context: Context) -> None:
    insert_block(context.page)
    fill_column_title(context.page, col_index=0, title="Link Column 1")
    fill_column_link(
        context.page,
        col_index=0,
        link_index=0,
        external_url="https://www.link-column-1.com/",
        link_title="",
    )


@then("an error message is displayed about the missing title")
def missing_title_error(context: Context) -> None:
    expect(context.page.locator("#columns-0-value-links-0-value-title-errors")).to_contain_text(
        "Title is required for external links."
    )


@when("the user adds a malformed URL")
def user_enters_incorrect_url(context: Context) -> None:
    insert_block(context.page)
    fill_column_title(context.page, col_index=0, title="Link Column 1")
    fill_column_link(
        context.page,
        col_index=0,
        link_index=0,
        external_url="htp:/malformed-url",
        link_title="Malformed URL",
    )


@then("an error message is displayed about the URL format")
def url_format_error(context: Context) -> None:
    expect(context.page.locator("#columns-0-value-links-0-value-external_url-errors")).to_contain_text(
        "Enter a valid URL."
    )


@when("the user adds more than 3 columns")
def user_inserts_more_than_max_columns(context: Context) -> None:
    generate_columns(context, num_columns=4)


@then("an error message is displayed about column limit")
def max_column_error(context: Context) -> None:
    expect(context.page.locator("#panel-columns-content")).to_contain_text("The maximum number of items is 3")


@when("the user adds more than 10 links")
def user_adds_above_max_links(context: Context) -> None:
    insert_block(context.page)
    fill_column_title(context.page, col_index=0, title="Link Column 1")

    for i in range(11):
        fill_column_link(
            context.page,
            col_index=0,
            link_index=i,
            external_url=f"https://www.link-column-1-link-{i}.com/",
            link_title=f"Link Title {i + 1}",
        )


@then("an error message is displayed about the link limit")
def max_link_error(context: Context) -> None:
    expect(context.page.locator("#panel-columns-content")).to_contain_text("The maximum number of items is 10")


@when("the user navigates to Snippets")
def user_navigates_to_snippets(context: Context) -> None:
    context.page.get_by_role("link", name="Snippets").click()


@when('the user clicks on "Footer menus"')
def user_clicks_footer_menus(context: Context) -> None:
    context.page.get_by_role("link", name="Footer menus").click()


@when('the user selects "More options for Footer Menu"')
def user_selects_more_options(context: Context) -> None:
    context.page.get_by_role("button", name="More options for 'Footer Menu'").click()


@when('the user clicks "Delete Footer Menu"')
def user_selects_delete_footer_menu(context: Context) -> None:
    context.page.get_by_role("link", name="Delete").click()
    context.page.get_by_role("button", name="Yes, delete").click()


@then("a banner confirming the deletion is displayed")
def user_sees_deletion_confirmation(context: Context) -> None:
    expect(context.page.get_by_text("Footer menu 'Footer Menu' deleted.")).to_be_visible()


@when("a footer menu is populated with 3 columns")
def create_populated_footer_menu(context: Context) -> None:
    generate_columns(context, num_columns=3)


@then("the footer menu appears on the home page")
def footer_menu_appears_on_home_page(context: Context) -> None:
    context.page.goto(context.base_url)

    column_headings = ["Link Column 1", "Link Column 2", "Link Column 3"]
    link_titles = ["Link Title 1", "Link Title 2", "Link Title 3"]

    for heading in column_headings:
        expect(context.page.get_by_role("heading", name=heading)).to_be_visible()

    contentinfo = context.page.get_by_role("contentinfo")
    for title in link_titles:
        expect(contentinfo).to_contain_text(title)
