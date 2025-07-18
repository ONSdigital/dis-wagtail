from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.core.custom_date_format import ons_default_datetime
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory


@given("a Release Calendar page with a publish notice exists")
def create_release_calendar_page(context: Context):
    context.release_calendar_page = ReleaseCalendarPageFactory(
        notice="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    )
    context.release_calendar_page.save_revision().publish()


@given("the user navigates to the release calendar page")
def navigate_to_release_page(context: Context):
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


@when('the user clicks "Add child page" to create a new draft release page')
def click_add_child_page(context: Context):
    context.page.get_by_label("Add child page").click()


@when("the user navigates to the published release calendar page")
def navigate_to_published_release_page(context: Context):
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.release_calendar_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the user returns to editing the release page")
def user_returns_to_editing_the_release_page(context: Context):
    context.page.get_by_role("link", name="Edit").click()


# datetime validation
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


@step('the date placeholder, "{time}", is displayed in the date input textboxes')
def date_placeholder_is_displayed_in_release_page_date_input_fields(context: Context, time: str):
    expect(context.page.locator("#id_release_date")).to_have_attribute("placeholder", time)
    expect(context.page.locator("#id_next_release_date")).to_have_attribute("placeholder", time)


@step("the user adds a release date text")
def add_release_date_with_text(context: Context):
    context.page.get_by_label("Or, release date text").fill("March 2025 to August 2025")


@then("the release date text is displayed")
def release_date_text_is_displayed(context: Context):
    expect(context.page.get_by_text("March 2025 to August 2025")).to_be_visible()


@step("the user adds a next release date text")
def add_next_release_date_with_text(context: Context):
    context.page.get_by_label("Or, next release date text").fill("To be confirmed")


@then("the next release date text is displayed")
def next_release_date_text_is_displayed(context: Context):
    expect(context.page.get_by_text("Next release date:")).to_be_visible()
    expect(context.page.get_by_text("To be confirmed")).to_be_visible()


@then("the default release date time is today's date and 9:30 AM")
def default_release_date_time_is_displayed(context: Context):
    default_datetime = ons_default_datetime().strftime("%Y-%m-%d %H:%M")
    expect(context.page.locator("#id_release_date")).to_have_value(default_datetime)


@then("the time selection options are in 30 minute intervals")
def thirty_minute_interval_for_time_selection(context: Context):
    time_picker = context.page.locator(".xdsoft_timepicker")
    hours = [f"{h:02}" for h in range(24)]

    context.page.get_by_role("textbox", name="Release date*").click()
    for hour in hours:
        expect(time_picker.get_by_text(f"{hour}:00").nth(2)).to_be_visible()
        expect(time_picker.get_by_text(f"{hour}:30").first).to_be_visible()

    context.page.get_by_role("textbox", name="Next release date", exact=True).click()
    for hour in hours:
        expect(time_picker.get_by_text(f"{hour}:00").nth(3)).to_be_visible()
        expect(time_picker.get_by_text(f"{hour}:30").nth(1)).to_be_visible()


# Release date and next release date
@when("the user adds a invalid release date text")
def user_inputs_invalid_release_date_text(context: Context):
    context.page.get_by_label("Or, release date text").fill("Invalid 4356")


@when("the user adds a invalid next release date text")
def user_inputs_invalid_next_release_date_text(context: Context):
    context.page.get_by_role("textbox", name="Or, next release date text").fill("Invalid 6444")


@then("an error message is displayed describing invalid next release date text input")
def error_invalid_next_release_date_text(context: Context):
    expect(context.page.get_by_text("The next release date text")).to_be_visible()
    expect(context.page.get_by_text("Format: 'DD Month YYYY Time'")).to_be_visible()


@then("an error message is displayed describing invalid release date text input")
def error_invalid_release_date_text(context: Context):
    expect(context.page.get_by_text("The release date text must be")).to_be_visible()
    expect(context.page.get_by_text("Override release date for")).to_be_visible()


@then("the date text field is not visible")
def check_date_text_field(context: Context):
    expect(context.page.get_by_text("Or, release date text")).not_to_be_visible()


@when("adds the next release date before the release date")
def user_add_next_release_date_before_release_date(context: Context):
    context.page.get_by_role("textbox", name="Release date*").fill("2024-12-25")
    context.page.locator("#id_next_release_date").fill("2023-12-25")


@when("the user enters both next release date and next release date text")
def user_adds_both_next_and_release_date(context: Context):
    context.page.locator("#id_next_release_date").fill("2025-12-25")
    context.page.locator("#id_next_release_date_text").fill("December 2025")


@then("an error validation is raised to say you cannot have both")
def error_cannot_have_both_next_release_date_and_text(context: Context):
    expect(context.page.get_by_text("The page could not be created")).to_be_visible()
    expect(
        context.page.locator(
            "#panel-child-content-child-metadata-child-panel1-child-next_release_date-errors"
        ).get_by_text("Please enter the next release")
    ).to_be_visible()
    expect(
        context.page.locator(
            "#panel-child-content-child-metadata-child-panel1-child-next_release_date_text-errors"
        ).get_by_text("Please enter the next release")
    ).to_be_visible()


@then("an error validation is raised to say next release date cannot be before release date")
def error_next_release_date_before_release_date(context: Context):
    expect(context.page.get_by_text("The page could not be created")).to_be_visible()
    expect(context.page.get_by_text("The next release date must be")).to_be_visible()


# Page creation, status and preview modes


@step('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str):
    context.page.get_by_label("Status*").select_option(page_status.upper())


@when('the user enters "Published" page content')
@when('the user enters "Provisional" page content')
@when('the user enters "Confirmed" page content')
@when("the user enters some example content on the page")
def enter_example_release_content(context: Context):
    page = context.page
    page.get_by_placeholder("Page title*").fill("My Release")

    page.get_by_role("textbox", name="Release date*").fill("2024-12-25")
    page.get_by_role("textbox", name="Release date*").press("Enter")

    page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").click()
    page.get_by_role("region", name="Release content").get_by_label("Title*").fill("My Example Content Link")

    page.get_by_role("button", name="Choose a page").click()
    page.get_by_label("Explore").click()
    page.get_by_role("link", name="Release calendar").click()

    page.get_by_label("Accredited Official Statistics").check()


@when('the user enters "Cancelled" page content')
def enter_cancelled_release_content(context: Context):
    context.page.locator(".public-DraftStyleDefault-block").first.fill("Notice cancelled")
    enter_example_release_content(context)


@when("the user adds contact details")
def add_contact_detail(context: Context):
    context.page.get_by_role("button", name="Choose contact details").click()
    context.page.get_by_role("link", name=context.contact_details_snippet.name).click()


@then("contact detail is displayed")
def displayed_contact_detail(context: Context):
    page = context.preview_page
    expect(page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()


@then("the release page displays example content")
def check_provisional_release_page_content(context: Context):
    page = context.page
    expect(page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")).to_be_visible()
    expect(page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then('the page status is set to "Provisional" and the release date text field is visible')
def check_that_default_status_is_provisional_and_release_date_text_is_visible(context: Context):
    expect(context.page.get_by_label("Status*")).to_have_value("PROVISIONAL")
    expect(context.page.get_by_text("Or, release date text")).to_be_visible()


@when('the user changes preview mode to "{page_status}"')
def user_changes_preview_mode(context: Context, page_status: str):
    context.page.get_by_label("Preview mode").select_option(page_status)


@when("the preview tab opened")
def open_preview_tab(context: Context):
    context.page.get_by_role("link", name="Preview in new tab").click()

    with context.page.expect_popup() as page1_info:
        context.page.get_by_role("link", name="Preview in new tab").click()
    context.preview_page = page1_info.value


@then('the "Provisional" page is displayed')
def display_provisional_page(context: Context):
    expect(context.page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Provisional" page is displayed in the preview page')
def preview_provisional_page(context: Context):
    expect(context.preview_page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Confirmed" page is displayed in the preview page')
def preview_confirmed_page(context: Context):
    expect(context.preview_page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Published" page is displayed in the preview page')
def preview_published_page(context: Context):
    page = context.preview_page
    expect(page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")).to_be_visible()
    expect(page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then('the "Cancelled" page is displayed in the preview page')
def preview_cancelled_page(context: Context):
    expect(context.preview_page.get_by_text("Cancelled", exact=True)).to_be_visible()


@then('the "Confirmed" page is displayed')
def display_confirmed_page(context: Context):
    expect(context.page.get_by_text("This release is not yet")).to_be_visible()


@then('the "Published" page is displayed')
def display_published_page(context: Context):
    page = context.page
    expect(page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")).to_be_visible()
    expect(page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then('the "Cancelled" page is displayed')
def display_cancelled_page(context: Context):
    expect(context.page.get_by_text("Cancelled", exact=True)).to_be_visible()
    expect(context.page.get_by_text("Notice cancelled")).to_be_visible()


@when("the user adds related links")
def add_related_links(context: Context):
    context.page.locator("#panel-child-content-related_links-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("link", name="Home").click()


@then("the related links is displayed")
def displayed_related_links(context: Context):
    expect(context.preview_page.get_by_role("heading", name="You might also be interested")).to_be_visible()
    expect(context.preview_page.locator("#links").get_by_role("link", name="Home")).to_be_visible()


@then("the release date change is displayed")
def displayed_date_change_log(context: Context):
    expect(context.preview_page.get_by_text("Updated due to data availability")).to_be_visible()


# Notice
@then("the notice field is disabled")
def check_notice_field_disabled(context: Context):
    expect(context.page.locator('[name="notice"]')).to_be_disabled()


@then("an error message is displayed describing notice must be added")
def error_cancelled_notice_must_be_added(context: Context):
    expect(context.page.get_by_text("The page could not be created")).to_be_visible()
    expect(context.page.get_by_text("The notice field is required")).to_be_visible()


# Prerelease access
@when("the user adds pre-release access information")
def add_pre_release_access(context: Context):
    page = context.page
    # Table
    page.locator("#panel-child-content-pre_release_access-content").get_by_role("button", name="Insert a block").click()
    page.get_by_text("Basic table").click()
    page.get_by_label("Table headers").select_option("column")
    page.get_by_role("textbox", name="Table caption").click()
    page.get_by_role("textbox", name="Table caption").fill("Caption")
    page.locator("td").first.click()
    page.keyboard.type("first")
    page.locator("td:nth-child(2)").first.click()
    page.keyboard.type("second")

    # Description
    page.locator("#panel-child-content-pre_release_access-content").get_by_role("button", name="Insert a block").nth(
        1
    ).click()
    page.get_by_role("option", name="Description").click()
    page.get_by_role("region", name="Description *").get_by_role("textbox").fill("Description")


@then("the pre-release access is displayed")
def displayed_pre_release_access(context: Context):
    page = context.preview_page
    expect(page.get_by_text("Pre-release access list")).to_be_visible()
    expect(page.get_by_text("first")).to_be_visible()
    expect(page.get_by_text("second")).to_be_visible()
    expect(page.get_by_text("Description")).to_be_visible()


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


# Release date changes
@step("the user adds a release date change")
def user_adds_a_release_date_change(context: Context):
    page = context.page
    change_to_release_date_section = page.locator("#panel-child-content-changes_to_release_date-section")
    change_to_release_date_section.get_by_role("button", name="Insert a block").click()
    change_to_release_date_section.get_by_label("Previous date*").fill("2024-12-20 14:30")
    change_to_release_date_section.get_by_label("Reason for change*").fill("Updated due to data availability")


@step("the user adds another release date change")
def user_adds_another_release_date_change(context: Context):
    page = context.page
    change_to_release_date_section = page.locator("#panel-child-content-changes_to_release_date-section")
    change_to_release_date_section.get_by_role("button", name="Insert a block").nth(1).click()
    change_to_release_date_section.get_by_label("Previous date*").nth(1).fill("2024-12-19 12:15")
    change_to_release_date_section.get_by_label("Reason for change*").nth(1).fill("New update to release schedule")


@then("the user cannot delete the release date change")
def user_cannot_delete_the_release_date_change(context: Context):
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    expect(
        page.locator("#panel-child-content-changes_to_release_date-section [data-streamfield-action='DELETE']")
    ).to_be_hidden()


@then("the user sees a validation error message about adding multiple release date changes")
def user_sees_validation_error_for_multiple_changes(context: Context):
    expect(
        context.page.get_by_text("Only one 'Changes to release date' entry can be added per release date change.")
    ).to_be_visible()


@then("the release calendar page is successfully updated")
def release_calendar_page_is_successfully_updated(context: Context):
    page = context.page
    expect(page.get_by_text("Page 'My Release' has been updated.")).to_be_visible()


@then("the release calendar page is successfully published")
def release_calendar_page_is_successfully_published(context: Context):
    page = context.page
    expect(page.get_by_text("Page 'My Release' has been published.")).to_be_visible()
