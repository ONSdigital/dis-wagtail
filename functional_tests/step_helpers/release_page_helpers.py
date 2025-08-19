from behave.runner import Context
from playwright.sync_api import expect

from functional_tests.step_helpers.footer_menu_helpers import choose_page_link

RELEASE_DATE = "#id_release_date"
RELEASE_DATE_TEXT = "#id_release_date_text"
NEXT_RELEASE_DATE = "#id_next_release_date"
NEXT_RELEASE_DATE_TEXT = "#id_next_release_date_text"


def fill_locator(context: Context, locator: str, text: str):
    context.page.locator(locator).fill(text)


def expect_text(context: Context, text: str, messages: dict[str, list[str]] | dict[str, str]):
    messages = messages.get(text)
    if isinstance(messages, str):
        messages = [messages]
    for message in messages:
        expect(context.page.get_by_text(message)).to_be_visible()


def add_release_date_change(context: Context):
    change_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    change_to_release_date_section.get_by_role("button", name="Insert a block").click()
    change_to_release_date_section.get_by_label("Reason for change*").fill("Updated due to data availability")


def handle_release_date_text(context: Context):
    fill_locator(context, RELEASE_DATE_TEXT, "March 2025 to August 2025")


def handle_next_release_date_text(context: Context):
    fill_locator(context, NEXT_RELEASE_DATE_TEXT, "To be confirmed")


def handle_related_link(context: Context):
    context.page.locator("#panel-child-content-related_links-content").get_by_role(
        "button", name="Insert a block"
    ).first.click()
    choose_page_link(context.page, page_name="Home")


def insert_block(context: Context, block_name: str, index: int = 0):
    """Inserts new empty block under pre-release access."""
    content_panel = context.page.locator("#panel-child-content-pre_release_access-content")

    content_panel.get_by_role("button", name="Insert a block").nth(index).click()
    context.page.get_by_role("option", name=block_name).click()


def add_basic_table(context: Context, data=True, header=True, index=0):
    """Inserts a table block and fills with content."""
    insert_block(context, block_name="Basic table", index=index)
    if header:
        context.page.get_by_label("Table headers").select_option("column")
    context.page.get_by_role("textbox", name="Table caption").fill("Caption")

    if data:
        context.page.locator("td").first.click()
        context.page.keyboard.type("first")
        context.page.locator("td:nth-child(2)").first.click()
        context.page.keyboard.type("second")


def add_description_block(context: Context, index=0):
    """Inserts description and fills with text under pre-release access."""
    insert_block(context, block_name="Description", index=index)
    context.page.get_by_role("region", name="Description *").get_by_role("textbox").fill("Description")


def handle_pre_release_access_info(context: Context):
    add_basic_table(context)
    add_description_block(context, index=1)


def handle_invalid_release_date(context: Context):
    fill_locator(context, RELEASE_DATE_TEXT, "Invalid 5555")


def handle_invalid_next_release_date(context: Context):
    fill_locator(context, NEXT_RELEASE_DATE_TEXT, "Invalid 5555")


def handle_next_to_be_before_release_date(context: Context):
    fill_locator(context, RELEASE_DATE, "2025-12-25")
    fill_locator(context, NEXT_RELEASE_DATE, "2024-12-25")


def handle_both_next_release_dates(context: Context):
    fill_locator(context, NEXT_RELEASE_DATE, "2025-12-25")
    fill_locator(context, NEXT_RELEASE_DATE_TEXT, "December 2024")


def expect_related_links(context: Context):
    expect(context.page.get_by_role("heading", name="You might also be interested")).to_be_visible()
    expect(context.page.locator("#links").get_by_role("link", name="Home")).to_be_visible()


def expect_not_both_dates_error(context: Context):
    expect(
        context.page.locator(
            "#panel-child-content-child-metadata-child-panel1-child-next_release_date-errors"
        ).get_by_text("Please enter the next release date or the next release text, not both.")
    ).to_be_visible()
    expect(
        context.page.locator(
            "#panel-child-content-child-metadata-child-panel1-child-next_release_date_text-errors"
        ).get_by_text("Please enter the next release date or the next release text, not both.")
    ).to_be_visible()


def handle_multiple_descriptions(context: Context):
    add_description_block(context)
    insert_block(context, block_name="Description", index=2)


def handle_multiple_tables(context: Context):
    insert_block(context, block_name="Basic table", index=0)
    insert_block(context, block_name="Basic table", index=1)


def handle_table_no_header(context: Context):
    add_basic_table(context, header=False)


def handle_empty_table(context: Context):
    add_basic_table(context, data=False)


def handle_release_date_change_no_log(context: Context):
    context.page.get_by_role("textbox", name="Release date*").fill("2025-01-25")


def handle_another_release_date_change(context: Context):
    section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    section.get_by_role("button", name="Insert a block").nth(1).click()
    section.get_by_label("Reason for change*").nth(1).fill("New update to release schedule")
