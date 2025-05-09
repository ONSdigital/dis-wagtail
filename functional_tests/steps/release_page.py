from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@given("the user navigates to the release calendar page")
def navigate_to_release_page(context: Context):
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


@when('the user clicks "Add child page" to create a new draft release page')
def click_add_child_page(context: Context):
    context.page.get_by_label("Add child page").click()


@step('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str):
    context.page.get_by_label("Status*").select_option(page_status.upper())


@when("the user enters some example content on the page")
def enter_example_release_content(context: Context):
    context.page.get_by_placeholder("Page title*").fill("My Release")

    context.page.get_by_role("textbox", name="Release date*").fill("2024-12-25")
    context.page.get_by_role("textbox", name="Release date*").press("Enter")

    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    context.page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("region", name="Release content").get_by_label("Title*").fill("My Example Content Link")

    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_label("Explore").click()
    context.page.get_by_role("link", name="Release calendar").click()

    context.page.get_by_role("button", name="Choose contact details").click()
    context.page.get_by_role("link", name=context.contact_details_snippet.name).click()

    context.page.get_by_label("Accredited Official Statistics").check()


@then("the new published release page with the example content is displayed")
def check_provisional_release_page_content(context: Context):
    expect(context.page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(context.page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(
        context.page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")
    ).to_be_visible()
    expect(context.page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(context.page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(context.page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()
    expect(context.page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then("the selected datasets are displayed on the page")
def check_selected_datasets_are_displayed(context: Context):
    expect(context.page.get_by_role("heading", name="Data", exact=True)).to_be_visible()

    for dataset in context.selected_datasets:
        expect(context.page.get_by_role("link", name=dataset["title"])).to_be_visible()
        expect(context.page.get_by_text(dataset["description"])).to_be_visible()


@then('the page status is set to "Provisional" and the release date text field is visible')
def check_that_default_status_is_provisional_and_release_date_text_is_visible(context: Context):
    expect(context.page.get_by_label("Status*")).to_have_value("PROVISIONAL")
    expect(context.page.get_by_text("Or, release date text")).to_be_visible()


@then("the date text field is not visible")
def check_date_text_field(context: Context):
    expect(context.page.get_by_text("Or, release date text")).not_to_be_visible()


@when("the user inputs a {meridiem_indicator} datetime")
def add_datetime(context: Context, meridiem_indicator: str):
    if meridiem_indicator == "am":
        context.page.get_by_role("textbox", name="Release date*").fill("2025-3-1 10:00")
    elif meridiem_indicator == "pm":
        context.page.get_by_role("textbox", name="Release date*").fill("2025-3-1 17:00")
    else:
        raise ValueError(f"Unsupported MeridiemIndicator: {meridiem_indicator}")


@then('the datetime is displayed with "{meridiem_indicator}"')
def display_datetime_with_meridiem(context: Context, meridiem_indicator: str):
    if meridiem_indicator == "am":
        expect(context.page.get_by_text("March 2025 10:00am")).to_be_visible()
    elif meridiem_indicator == "pm":
        expect(context.page.get_by_text("March 2025 5:00pm")).to_be_visible()
    else:
        raise ValueError(f"Unsupported MeridiemIndicator: {meridiem_indicator}")


@step('by label, the date placeholder "{date_format}" is displayed in the "{textbox_text}" textbox')
def date_placeholder(context: Context, textbox_text: str, date_format: str):
    """Check date placeholder in the textbox."""
    expect(context.page.get_by_label(textbox_text)).to_have_attribute("placeholder", date_format)
