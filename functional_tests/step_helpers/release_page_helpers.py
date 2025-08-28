from collections.abc import Callable, Mapping, Sequence

from behave.runner import Context
from playwright.sync_api import expect

from functional_tests.step_helpers.footer_menu_helpers import choose_page_link

RELEASE_DATE = "#id_release_date"
RELEASE_DATE_TEXT = "#id_release_date_text"
NEXT_RELEASE_DATE = "#id_next_release_date"
NEXT_RELEASE_DATE_TEXT = "#id_next_release_date_text"


def fill_locator(context: Context, locator: str, text: str) -> None:
    context.page.locator(locator).fill(text)


# 'index' parameter is used when inserting blocks because when multiple blocks are inserted,
# button may shift causing inconsistent increments in the block indices (e.g. add_multiple_descriptions)
def insert_block_under_pre_release_access(context: Context, block_name: str, index: int = 0) -> None:
    """Inserts new empty block under pre-release access."""
    content_panel = context.page.locator("#panel-child-content-pre_release_access-content")

    content_panel.get_by_role("button", name="Insert a block").nth(index).click()
    context.page.get_by_role("option", name=block_name).click()


def add_basic_table_block_under_pre_release_access(context: Context, data: bool = True, header: bool = True) -> None:
    """Inserts a table block and fills with content."""
    insert_block_under_pre_release_access(context, block_name="Basic table")
    if header:
        context.page.get_by_label("Table headers").select_option("column")
    context.page.get_by_role("textbox", name="Table caption").fill("Caption")

    if data:
        context.page.locator("td").first.click()
        context.page.keyboard.type("Name")
        context.page.locator("td:nth-child(2)").first.click()
        context.page.keyboard.type("Role")
        context.page.locator("td").first.click()
        context.page.keyboard.type("Heading")
        context.page.locator("tr:nth-child(2) > td").first.click()
        context.page.keyboard.type("Jack Smith")
        context.page.locator("tr:nth-child(2) > td:nth-child(2)").first.click()
        context.page.keyboard.type("Publisher")


def add_description_block_under_pre_release_access(context: Context, index: int = 0) -> None:
    """Inserts description and fills with text under pre-release access."""
    insert_block_under_pre_release_access(context, block_name="Description", index=index)
    context.page.get_by_role("region", name="Description *").get_by_role("textbox").fill("Description")


def expect_text(
    context: Context,
    key: str | None,
    texts: Sequence[str] | dict[str, str] | Mapping[str, str | Sequence[str]],
) -> None:
    """Checks that one or more expected texts are visible on the page."""
    if key:
        texts = texts.get(key)
    if isinstance(texts, str):
        texts = [texts]
    for text in texts:
        expect(context.page.get_by_text(text)).to_be_visible()


def expect_changes_to_release_date(context: Context) -> None:
    preview_texts: list[str] = [
        "Previous date",
        "25 December 2024 9:30am",
        "Reason for change",
        "Updated due to data availability",
    ]
    expect_text(context, key=None, texts=preview_texts)
    expect(context.page.get_by_role("link", name="Changes to this release date")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Changes to this release date")).to_be_visible()


def add_another_release_date_change(context: Context) -> None:
    section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    section.get_by_role("button", name="Insert a block").nth(1).click()
    section.get_by_label("Reason for change*").nth(1).fill("New update to release schedule")


# Dispatcher mapping
FEATURE_ACTIONS: dict[str, Callable[[Context], None]] = {
    "a release date text": lambda ctx: fill_locator(ctx, RELEASE_DATE_TEXT, "March 2025 to August 2025"),
    "a next release date text": lambda context: fill_locator(context, NEXT_RELEASE_DATE_TEXT, "To be confirmed"),
    "a related link": lambda ctx: (
        ctx.page.locator("#panel-child-content-related_links-content")
        .get_by_role("button", name="Insert a block")
        .first.click(),
        choose_page_link(ctx.page, page_name="Home"),
    ),
    "pre-release access information": lambda ctx: (
        add_basic_table_block_under_pre_release_access(ctx),
        add_description_block_under_pre_release_access(ctx, index=1),
    ),
    "a date change log": lambda ctx: (
        ctx.page.locator("#panel-child-content-changes_to_release_date-section")
        .get_by_role("button", name="Insert a block")
        .click(),
        ctx.page.locator("#panel-child-content-changes_to_release_date-section")
        .get_by_label("Reason for change*")
        .fill("Updated due to data availability"),
    ),
    "an invalid release date text": lambda ctx: fill_locator(ctx, RELEASE_DATE_TEXT, "Invalid 5555"),
    "an invalid next release date text": lambda ctx: fill_locator(ctx, NEXT_RELEASE_DATE_TEXT, "Invalid 5555"),
    ("the next release date is set to a date earlier than the release date"): lambda ctx: (
        fill_locator(ctx, RELEASE_DATE, "2025-12-25"),
        fill_locator(ctx, NEXT_RELEASE_DATE, "2024-12-25"),
    ),
    "both next release date and next release date text": lambda ctx: (
        fill_locator(ctx, NEXT_RELEASE_DATE, "2025-12-25"),
        fill_locator(ctx, NEXT_RELEASE_DATE_TEXT, "December 2024"),
    ),
}


# Preview display logic for features
def display_feature_in_preview_tab(context: Context, feature: str) -> None:
    preview_texts: dict[str, Sequence[str]] = {
        "a release date text": "March 2025 to August 2025",
        "a next release date text": ["Next release date:", "To be confirmed"],
        "pre-release access information": [
            "Pre-release access list",
            "Name",
            "Role",
            "Jack Smith",
            "Publisher",
        ],
    }

    custom_handlers: dict[str, Callable[[Context], None]] = {
        "a related link": lambda ctx: (
            expect(ctx.page.get_by_role("heading", name="You might also be interested")).to_be_visible(),
            expect(ctx.page.locator("#links").get_by_role("link", name="Home")).to_be_visible(),
        ),
        "a release date change": expect_changes_to_release_date,
    }

    if feature in custom_handlers:
        custom_handlers[feature](context)
    elif feature in preview_texts:
        expect_text(context, feature, preview_texts)
    else:
        raise ValueError(f"Unsupported feature: {feature}")


# Error message and handler logic for release calendar page validation errors
def handle_release_calendar_page_errors(context: Context, error: str) -> None:
    error_messages: dict[str, str] = {
        "invalid release date text input": (
            "The release date text must be in the 'Month YYYY' or 'Month YYYY to Month YYYY' format in English."
        ),
        "invalid next release date text input": (
            'The next release date text must be in the "DD Month YYYY Time" format or say "To be confirmed" in English'
        ),
        "next release date cannot be before release date": ("The next release date must be after the release date."),
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

    custom_handlers: dict[str, Callable[[Context], None]] = {
        ("cannot have both next release date and next release date text"): lambda ctx: (
            expect(
                ctx.page.locator(
                    "#panel-child-content-child-metadata-child-panel1-child-next_release_date-errors"
                ).get_by_text("Please enter the next release date or the next release text, not both.")
            ).to_be_visible(),
            expect(
                ctx.page.locator(
                    "#panel-child-content-child-metadata-child-panel1-child-next_release_date_text-errors"
                ).get_by_text("Please enter the next release date or the next release text, not both.")
            ).to_be_visible(),
        ),
    }

    if error in custom_handlers:
        custom_handlers[error](context)
    elif error in error_messages:
        expect_text(context, error, error_messages)
    else:
        raise ValueError(f"Unsupported error: {error}")


def handle_pre_release_access_feature(context: Context, feature: str) -> None:
    """Handle adding features under pre-release access, mapping feature strings to their respective actions."""
    handlers: dict[str, Callable[[Context], None]] = {
        "multiple descriptions are": lambda ctx: (
            add_description_block_under_pre_release_access(ctx),
            insert_block_under_pre_release_access(ctx, block_name="Description", index=2),
        ),
        "multiple tables are": lambda ctx: (
            insert_block_under_pre_release_access(ctx, block_name="Basic table"),
            insert_block_under_pre_release_access(ctx, block_name="Basic table", index=1),
        ),
        "a table with no table header selected is": lambda ctx: add_basic_table_block_under_pre_release_access(
            ctx, header=False
        ),
        "an empty table is": lambda ctx: add_basic_table_block_under_pre_release_access(ctx, data=False),
    }

    handler = handlers.get(feature)
    if handler:
        handler(context)
    else:
        raise ValueError(f"Unsupported feature: {feature}")


def handle_changes_to_release_date_feature(
    context: Context, feature: str, add_feature: Callable[[Context], None]
) -> None:
    """Handle adding features under changes to release date, mapping feature strings to their respective actions."""
    handlers = {
        "multiple date change logs": lambda ctx: (
            add_feature(ctx, "a date change log"),
            add_another_release_date_change(ctx),
        ),
        "a release date change with no date change log": lambda ctx: ctx.page.get_by_role(
            "textbox", name="Release date*"
        ).fill("2025-01-25"),
        "a date change log with no release date change": lambda ctx: add_feature(ctx, "a date change log"),
        "another date change log": add_another_release_date_change,
    }
    handler = handlers.get(feature)
    if handler:
        handler(context)
    else:
        raise ValueError(f"Unsupported feature: {feature}")
