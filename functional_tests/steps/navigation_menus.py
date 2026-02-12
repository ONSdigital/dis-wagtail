# pylint: disable=not-callable
from behave import given, step, then, when
from behave.runner import Context
from playwright.sync_api import expect

from cms.navigation.tests.factories import FooterMenuFactory
from functional_tests.step_helpers.navigation_menus_helpers import (
    choose_page_link,
    fill_column_link,
    fill_column_title,
    generate_columns,
    generate_full_main_menu,
    insert_block,
)


@given("a footer menu exists")
def create_footer_menu(context: Context) -> None:
    context.footer_menu = FooterMenuFactory()


@when("the user opens an existing {menu_type} menu for editing")
def user_opens_existing_menu(context: Context, menu_type: str) -> None:
    context.page.get_by_role("link", name="Snippets").click()
    context.page.get_by_role("link", name=f"{menu_type.capitalize()} menus").click()
    context.page.get_by_role("link", name=f"{menu_type.capitalize()} Menu (English)").click()


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


@then("the footer menu is displayed on the homepage with an external link")
def footer_menu_homepage_external_link(context: Context) -> None:
    context.page.goto(context.base_url)
    expect(context.page.get_by_role("heading", name="Link Column")).to_be_visible()
    expect(context.page.get_by_role("contentinfo")).to_contain_text("Link Title 1")


@then("a banner confirming changes is displayed")
def footer_menu_banner_confirmation(context: Context) -> None:
    expect(context.page.get_by_text("Footer menu 'Footer Menu'")).to_be_visible()


@then("the footer menu is displayed on the preview pane with an external link")
def populated_footer_menu_preview_pane(context: Context) -> None:
    iframe_locator = context.page.frame_locator("#w-preview-iframe")
    expect(iframe_locator.get_by_role("heading", name="Link Column 1")).to_be_visible()
    expect(iframe_locator.get_by_role("link", name="Link Title 1")).to_be_visible()


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


@when("the footer menu is populated with 3 columns")
def create_populated_footer_menu(context: Context) -> None:
    generate_columns(context, num_columns=3)


@when("the main menu is populated with 3 columns")
def create_populated_main_menu(context: Context) -> None:
    generate_full_main_menu(context.page)


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
