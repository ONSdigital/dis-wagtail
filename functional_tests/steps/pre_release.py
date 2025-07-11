from behave import then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@when("multiple descriptions are added under pre-release access")
def add_multiple_description(context: Context):
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_role("option", name="Description").click()
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).nth(2).click()
    context.page.get_by_role("option", name="Description").click()


@then("an error message is displayed about the descriptions")
def error_multiple_description(context: Context):
    expect(context.page.get_by_text("Description: The maximum")).to_be_visible()


@when("multiple tables are added under pre-release access")
def add_multiple_tables(context: Context):
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_text("Basic table").click()
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).nth(1).click()
    context.page.locator("#downshift-7-item-1").get_by_text("Basic table").click()


@then("an error message is displayed about the tables")
def error_multiple_tables(context: Context):
    expect(context.page.get_by_text("Basic table: The maximum")).to_be_visible()


@then("an error message is displayed to select and option")
def error_unpicked_table_option(context: Context):
    expect(context.page.get_by_text("The page could not be saved")).to_be_visible()
    expect(context.page.get_by_text("Select an option for Table")).to_be_visible()


@then("an error message is displayed about empty table")
def error_empty_table(context: Context):
    expect(context.page.get_by_text("The page could not be saved")).to_be_visible()
    expect(context.page.get_by_text("The table cannot be empty")).to_be_visible()


# try content
@when("the user adds pre-release access information")
def add_pre_release_access(context: Context):
    # Table
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_text("Basic table").click()
    context.page.get_by_label("Table headers").select_option("row")
    context.page.get_by_role("textbox", name="Table caption").click()
    context.page.get_by_role("textbox", name="Table caption").fill("Caption")
    context.page.locator("td").first.fill("head")

    # Description
    context.page.locator("#panel-child-content-pre_release_access-content").get_by_role(
        "button", name="Insert a block"
    ).nth(1).click()
    context.page.get_by_role("option", name="Description").click()
    context.page.get_by_role("region", name="Description *").get_by_role("textbox").fill("Description")


# Fails as the filled table empties upon saving
@then("the pre-release access is displayed")
def displayed_pre_release_access(context: Context):
    page = context.preview_page
    expect(page.get_by_text("Pre-release access list")).to_be_visible()
    expect(page.get_by_text("head")).to_be_visible()
    expect(page.get_by_text("Description")).to_be_visible()
