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


@step('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str):
    context.page.get_by_label("Status*").select_option(page_status.upper())


@when("the user enters some example content on the page")
def enter_example_release_content(context: Context):
    page = context.page
    page.get_by_placeholder("Page title*").fill("My Release")

    page.get_by_role("textbox", name="Release date*").fill("2024-12-25 09:30")
    page.get_by_role("textbox", name="Release date*").press("Enter")

    page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").click()
    page.get_by_role("region", name="Release content").get_by_label("Title*").fill("My Example Content Link")

    page.get_by_role("button", name="Choose a page").click()
    page.get_by_label("Explore").click()
    page.get_by_role("link", name="Release calendar").click()

    page.get_by_role("button", name="Choose contact details").click()
    page.get_by_role("link", name=context.contact_details_snippet.name).click()

    page.get_by_label("Accredited Official Statistics").check()


@then("the new published release page with the example content is displayed")
def check_provisional_release_page_content(context: Context):
    page = context.page
    expect(page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")).to_be_visible()
    expect(page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()
    expect(page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then('the page status is set to "Provisional" and the release date text field is visible')
def check_that_default_status_is_provisional_and_release_date_text_is_visible(context: Context):
    expect(context.page.get_by_label("Status*")).to_have_value("PROVISIONAL")
    expect(context.page.get_by_text("Or, release date text")).to_be_visible()


@then("the date text field is not visible")
def check_date_text_field(context: Context):
    expect(context.page.get_by_text("Or, release date text")).not_to_be_visible()


@then("the notice field is disabled")
def check_notice_field_disabled(context: Context):
    expect(context.page.locator('[name="notice"]')).to_be_disabled()


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


@when("user navigates to edit page")
def user_edits_published_page(context: Context):
    page = context.page
    page.get_by_role("link", name="My Release", exact=True).click()
    page.get_by_role("button", name="Pages").click()
    page.get_by_role("link", name="View child pages of 'Home'").first.click()
    page.get_by_role("link", name="View child pages of 'Release").click()
    page.get_by_role("link", name="Edit 'My Release'").click()


@step("the user returns to editing the release page")
def user_returns_to_editing_the_release_page(context: Context):
    context.page.get_by_role("link", name="Edit").click()


@step("the user adds a release date change")
def user_adds_a_release_date_change(context: Context):
    page = context.page
    change_to_release_date_section = page.locator("#panel-child-content-changes_to_release_date-section")
    change_to_release_date_section.get_by_role("button", name="Insert a block").click()
    change_to_release_date_section.get_by_label("Reason for change*").fill("Updated due to data availability")


@step("the user adds another release date change")
def user_adds_another_release_date_change(context: Context):
    page = context.page
    change_to_release_date_section = page.locator("#panel-child-content-changes_to_release_date-section")
    change_to_release_date_section.get_by_role("button", name="Insert a block").nth(1).click()
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


@then("the previous release date field is not editable")
def previous_release_date_field_is_not_editable(context: Context):
    changes_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    expect(changes_to_release_date_section.get_by_label("Previous date*")).not_to_be_editable()


@when("the user changes the release date to a new date")
def user_changes_release_date_to_new_date(context: Context):
    context.page.get_by_role("textbox", name="Release date*").fill("2024-12-21 15:00")


@then("the previous release date field is pre-populated with the old release date")
def previous_release_date_field_is_pre_populated(context: Context):
    changes_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    expect(changes_to_release_date_section.get_by_label("Previous date*")).to_have_value("2024-12-25 09:30")


@then("the Changes to release date block is not visible")
def previous_release_date_in_date_change_block_is_empty(context: Context):
    expect(context.page.locator("#panel-child-content-changes_to_release_date-section")).not_to_be_visible()


@then("the help text is not visible")
def help_text_is_not_visible(context: Context):
    changes_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    expect(
        changes_to_release_date_section.get_by_text("This field will be auto-populated once the page is saved.")
    ).not_to_be_visible()


@then("the help text is visible")
def help_text_is_visible(context: Context):
    changes_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    expect(
        changes_to_release_date_section.get_by_text("This field will be auto-populated once the page is saved.")
    ).to_be_visible()
