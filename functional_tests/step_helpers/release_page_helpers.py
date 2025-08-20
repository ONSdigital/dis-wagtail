from collections.abc import Callable

from behave.runner import Context
from playwright.sync_api import expect

from functional_tests.step_helpers.footer_menu_helpers import choose_page_link

RELEASE_DATE = "#id_release_date"
RELEASE_DATE_TEXT = "#id_release_date_text"
NEXT_RELEASE_DATE = "#id_next_release_date"
NEXT_RELEASE_DATE_TEXT = "#id_next_release_date_text"


def fill_locator(context: Context, locator: str, text: str):
    context.page.locator(locator).fill(text)


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


def expect_text(context: Context, text: str, messages: dict[str, list[str]] | dict[str, str]):
    messages = messages.get(text)
    if isinstance(messages, str):
        messages = [messages]
    for message in messages:
        expect(context.page.get_by_text(message)).to_be_visible()


def add_date_change_log(context: Context):
    change_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    change_to_release_date_section.get_by_role("button", name="Insert a block").click()
    change_to_release_date_section.get_by_label("Reason for change*").fill("Updated due to data availability")


def add_release_date_text(context: Context):
    fill_locator(context, RELEASE_DATE_TEXT, "March 2025 to August 2025")


def add_next_release_date_text(context: Context):
    fill_locator(context, NEXT_RELEASE_DATE_TEXT, "To be confirmed")


def add_related_link(context: Context):
    context.page.locator("#panel-child-content-related_links-content").get_by_role(
        "button", name="Insert a block"
    ).first.click()
    choose_page_link(context.page, page_name="Home")


def add_pre_release_access_info(context: Context):
    add_basic_table(context)
    add_description_block(context, index=1)


def add_invalid_release_date_text(context: Context):
    fill_locator(context, RELEASE_DATE_TEXT, "Invalid 5555")


def add_invalid_next_release_date_text(context: Context):
    fill_locator(context, NEXT_RELEASE_DATE_TEXT, "Invalid 5555")


def add_next_release_before_release(context: Context):
    fill_locator(context, RELEASE_DATE, "2025-12-25")
    fill_locator(context, NEXT_RELEASE_DATE, "2024-12-25")


def add_both_next_release_dates(context: Context):
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


def add_multiple_descriptions(context: Context):
    add_description_block(context)
    insert_block(context, block_name="Description", index=2)


def add_multiple_tables(context: Context):
    insert_block(context, block_name="Basic table", index=0)
    insert_block(context, block_name="Basic table", index=1)


def add_table_no_header(context: Context):
    add_basic_table(context, header=False)


def add_empty_table(context: Context):
    add_basic_table(context, data=False)


def add_release_date_change_no_log(context: Context):
    context.page.get_by_role("textbox", name="Release date*").fill("2025-01-25")


def add_another_release_date_change(context: Context):
    section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    section.get_by_role("button", name="Insert a block").nth(1).click()
    section.get_by_label("Reason for change*").nth(1).fill("New update to release schedule")


# Dispatcher mapping
FEATURE_ACTIONS: dict[str, Callable[[Context], None]] = {
    "a release date text": add_release_date_text,
    "a next release date text": add_next_release_date_text,
    "a related link": add_related_link,
    "pre-release access information": add_pre_release_access_info,
    "a date change log": add_date_change_log,
    "an invalid release date text": add_invalid_release_date_text,
    "an invalid next release date text": add_invalid_next_release_date_text,
    "the next release date to be before the release date": add_next_release_before_release,
    "both next release date and next release date text": add_both_next_release_dates,
}


# Preview display logic for features
def display_feature_in_preview_tab(context: Context, feature: str):
    preview_texts: dict[str, list[str] | str] = {
        "a release date text": "March 2025 to August 2025",
        "a next release date text": ["Next release date:", "To be confirmed"],
        "pre-release access information": [
            "Pre-release access list",
            "first",
            "second",
            "Description",
        ],
        "a release date change": [
            "Changes to this release date",
            "Previous date",
            "25 December 2024 9:30am",
            "Reason for change",
            "Updated due to data availability",
        ],
    }

    custom_handlers: dict[str, Callable[[Context], None]] = {
        "a related link": expect_related_links,
    }

    if feature in custom_handlers:
        custom_handlers[feature](context)
    elif feature in preview_texts:
        expect_text(context, feature, preview_texts)
    else:
        raise ValueError(f"Unsupported feature: {feature}")


# Error message and handler logic for release calendar page validation errors
def handle_release_calendar_page_errors(context, error):
    error_messages = {
        "invalid release date text input": (
            "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format in English."
        ),
        "invalid next release date text input": (
            'The next release date text must be in the "DD Month YYYY Time" format or say "To be confirmed" in English'
        ),
        "next release date cannot be before release date": ("The next release date must be after the release date."),
        "cannot have both next release date and next release date text": None,
        "a cancellation notice must be added": "The notice field is required when the release is cancelled",
        "multiple release date change logs": (
            "Only one 'Changes to release date' entry can be added per release date change."
        ),
        "maximum descriptions allowed": "Description: The maximum number of items is 1",
        "maximum tables allowed": "Basic table: The maximum number of items is 1",
        "unselected options": "Select an option for Table headers",
        "empty tables are not allowed": "The table cannot be empty",
        "release date change with no date change log": (
            "If a confirmed calendar entry needs to be rescheduled, the 'Changes to release date' "
            "field must be filled out."
        ),
        "date change log with no release date change": (
            "You have added a 'Changes to release date' entry, but the release date is the same "
            "as the published version."
        ),
    }

    custom_handlers = {
        "cannot have both next release date and next release date text": expect_not_both_dates_error,
    }

    if error in custom_handlers:
        custom_handlers[error](context)
    elif error in error_messages:
        expect_text(context, error, error_messages)
    else:
        raise ValueError(f"Unsupported error: {error}")


def handle_pre_release_access_feature(context, feature):
    """Handle adding features under pre-release access, mapping feature strings to their respective actions."""
    handlers = {
        "multiple descriptions are": add_multiple_descriptions,
        "multiple tables are": add_multiple_tables,
        "a table with no table header selected is": add_table_no_header,
        "an empty table is": add_empty_table,
    }

    handler = handlers.get(feature)
    if handler:
        handler(context)
    else:
        raise ValueError(f"Unsupported feature: {feature}")


def handle_changes_to_release_date_feature(context, feature, add_feature):
    """Handle adding features under changes to release date, mapping feature strings to their respective actions."""
    handlers = {
        "multiple date change logs": lambda ctx: (
            add_feature(ctx, "a date change log"),
            add_another_release_date_change(ctx),
        ),
        "a release date change with no date change log": add_release_date_change_no_log,
        "a date change log with no release date change": lambda ctx: add_feature(ctx, "a date change log"),
        "another date change log": add_another_release_date_change,
    }

    handler = handlers.get(feature)
    if handler:
        handler(context)
    else:
        raise ValueError(f"Unsupported feature: {feature}")
