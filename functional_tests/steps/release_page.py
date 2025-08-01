from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.core.custom_date_format import ons_default_datetime
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from functional_tests.step_helpers.footer_menu_helpers import choose_page_link
from functional_tests.step_helpers.pre_release_access_helpers import (
    add_basic_table,
    add_description_block,
    insert_block,
)
from functional_tests.steps.page_editor import user_clicks_publish


@given("a Release Calendar page with a published notice exists")
def create_release_calendar_page(context: Context):
    context.release_calendar_page = ReleaseCalendarPageFactory(
        notice="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    )
    context.release_calendar_page.save_revision().publish()


@given("the user navigates to the release calendar page")
def navigate_to_release_calendar_page(context: Context):
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


@then("the notice field is disabled")
def check_notice_field_disabled(context: Context):
    expect(context.page.locator('[name="notice"]')).to_be_disabled()


@when('the user clicks "Add child page" to create a new draft release page')
def click_add_child_page(context: Context):
    context.page.get_by_label("Add child page").click()


@when("the user navigates to the published release calendar page")
def navigate_to_published_release_calendar_page(context: Context):
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.release_calendar_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@then("the default release date is today's date and 9:30 AM")
def default_release_date_time_is_displayed(context: Context):
    default_datetime = ons_default_datetime().strftime("%Y-%m-%d %H:%M")
    expect(context.page.locator("#id_release_date")).to_have_value(default_datetime)


@step('the datetime placeholder, "{time}", is displayed in the release date input field')
def datetime_placeholder_is_displayed_in_release_page_date_input_fields(context: Context, time: str):
    expect(context.page.locator("#id_release_date")).to_have_attribute("placeholder", time)
    expect(context.page.locator("#id_next_release_date")).to_have_attribute("placeholder", time)


@then("in the datetime selector, the time selection options are in 30 minute intervals")
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


@when('the user enters "{page_status}" page content')
@when("the user enters some example content on the page")
def user_enters_example_content_on_release_page(context: Context, page_status: str | None = None):
    if page_status == "Cancelled":
        context.page.locator(".public-DraftStyleDefault-block").first.fill("Notice cancelled")
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

    page.get_by_role("button", name="Choose contact details").click()
    page.get_by_role("link", name=context.contact_details_snippet.name).click()


@step('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str):
    context.page.get_by_label("Status*").select_option(page_status.upper())


@then('the "{page_status}" page is displayed')
def display_published_page_for_correct_page_status(context: Context, page_status: str):
    if page_status in ("Provisional", "Confirmed"):
        expect(context.page.get_by_text("This release is not yet published")).to_be_visible()
    elif page_status == "Cancelled":
        expect(context.page.get_by_text("Cancelled", exact=True)).to_be_visible()
        expect(context.page.get_by_text("Notice cancelled")).to_be_visible()
    else:
        raise ValueError(f"Unsupported page status: {page_status}")


@then("the example content is displayed in the preview tab")
def display_example_content_release_page_in_preview_tab(context: Context):
    page = context.page
    expect(page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")).to_be_visible()
    expect(page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()
    expect(page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then('the "{preview_mode}" page is displayed in the preview tab')
def display_release_page_in_preview_mode_in_preview_tab(context: Context, preview_mode: str):
    page = context.page
    if preview_mode in ("Provisional", "Confirmed"):
        expect(page.get_by_text("This release is not yet")).to_be_visible()
    elif preview_mode == "Cancelled":
        expect(page.get_by_text("Cancelled", exact=True)).to_be_visible()
    elif preview_mode == "Published":
        display_example_content_release_page_in_preview_tab(context)
    else:
        raise ValueError(f"Unsupported preview mode: {preview_mode}")


@step("the user adds {feature} to the release calendar page")
def add_feature(context: Context, feature: str):
    page = context.page
    if feature == "a release date text":
        page.get_by_label("Or, release date text").fill("March 2025 to August 2025")
    elif feature == "a next release date text":
        page.get_by_label("Or, next release date text").fill("To be confirmed")
    elif feature == "a related link":
        page.locator("#panel-child-content-related_links-content").get_by_role("button", name="Insert a block").click()
        choose_page_link(page, page_name="Home")
    elif feature == "pre-release access information":
        add_basic_table(context)
        add_description_block(context, index=1)
    elif feature == "a release date change":
        change_to_release_date_section = page.locator("#panel-child-content-changes_to_release_date-section")
        change_to_release_date_section.get_by_role("button", name="Insert a block").click()
        change_to_release_date_section.get_by_label("Previous date*").fill("2024-12-20 14:30")
        change_to_release_date_section.get_by_label("Reason for change*").fill("Updated due to data availability")

    elif feature == "an invalid release date text":
        context.page.get_by_label("Or, release date text").fill("Invalid 4356")
    elif feature == "an invalid next release date text":
        context.page.get_by_role("textbox", name="Or, next release date text").fill("Invalid 6444")
    elif feature == "the next release date to be before the release date":
        context.page.get_by_role("textbox", name="Release date*").fill("2024-12-25")
        context.page.locator("#id_next_release_date").fill("2023-12-25")
    elif feature == "both next release date and next release date text":
        context.page.locator("#id_next_release_date").fill("2025-12-25")
        context.page.locator("#id_next_release_date_text").fill("December 2025")

    else:
        raise ValueError(f"Unsupported page feature: {feature}")


@then("{feature} is displayed in the release calendar page preview tab")
def display_features_in_preview_tab(context: Context, feature: str):
    page = context.page
    if feature == "a release date text":
        expect(page.get_by_text("March 2025 to August 2025")).to_be_visible()
    elif feature == "a next release date text":
        expect(page.get_by_text("Next release date:")).to_be_visible()
        expect(page.get_by_text("To be confirmed")).to_be_visible()
    elif feature == "a related link":
        expect(page.get_by_role("heading", name="You might also be interested")).to_be_visible()
        expect(page.locator("#links").get_by_role("link", name="Home")).to_be_visible()
    elif feature == "pre-release access information":
        expect(page.get_by_text("Pre-release access list")).to_be_visible()
        expect(page.get_by_text("first")).to_be_visible()
        expect(page.get_by_text("second")).to_be_visible()
        expect(page.get_by_text("Description")).to_be_visible()
    elif feature == "a release date change":
        # add date
        expect(page.get_by_text("Updated due to data availability")).to_be_visible()
    else:
        raise ValueError(f"Unsupported page feature: {feature}")


@then('the page status is set to "Provisional" and the release date text field is visible')
def check_that_default_status_is_provisional_and_release_date_text_is_visible(
    context: Context,
):
    expect(context.page.get_by_label("Status*")).to_have_value("PROVISIONAL")
    expect(context.page.get_by_text("Or, release date text")).to_be_visible()


@then("the date text field is not visible")
def check_date_text_field(context: Context):
    expect(context.page.get_by_text("Or, release date text")).not_to_be_visible()


@then("an error message is displayed to say the page could not be created")
def error_page_not_created(context: Context):
    expect(context.page.get_by_text("The page could not be created due to validation errors")).to_be_visible()


@then("the user sees a validation error message: {error}")
def error_invalid_release_calendar_page_input(context: Context, error: str):
    page = context.page
    if error == "invalid release date text input":
        expect(page.get_by_text("The release date text must be")).to_be_visible()
        expect(page.get_by_text("Override release date for")).to_be_visible()
    elif error == "invalid next release date text input":
        expect(page.get_by_text("The next release date text")).to_be_visible()
        expect(page.get_by_text("Format: 'DD Month YYYY Time'")).to_be_visible()
    elif error == "next release date cannot be before release date":
        expect(page.get_by_text("The next release date must be")).to_be_visible()
    elif error == "cannot have both next release date and next release date text":
        expect(
            page.locator("#panel-child-content-child-metadata-child-panel1-child-next_release_date-errors").get_by_text(
                "Please enter the next release date or the next release text, not both."
            )
        ).to_be_visible()
        expect(
            page.locator(
                "#panel-child-content-child-metadata-child-panel1-child-next_release_date_text-errors"
            ).get_by_text("Please enter the next release date or the next release text, not both.")
        ).to_be_visible()

    # Notice error
    elif error == "a notice must be added":
        expect(context.page.get_by_text("The notice field is required when the release is cancelled")).to_be_visible()

    else:
        raise ValueError(f"Unsupported page feature: {error}")


@when("{feature} added under pre-release access")
def add_pre_release_access_info(context: Context, feature: str):
    if feature == "multiple descriptions are":
        add_description_block(context)
        insert_block(context, block_name="Description", index=2)
    elif feature == "multiple tables are":
        insert_block(context, block_name="Basic table", index=0)
        insert_block(context, block_name="Basic table", index=1)
    elif feature == "a table with no table header selected is":
        add_basic_table(context, header=False)
    elif feature == "an empty table is":
        add_basic_table(context, data=False)
    else:
        raise ValueError(f"Unsupported feature: {feature}")


# could combine with other error messages
@then("under pre-release access, the user sees a validation error message: {error}")
def error_invalid_pre_release_access(context: Context, error: str):
    if error == "maximum descriptions allowed":
        expect(context.page.get_by_text("Description: The maximum number of items is 1")).to_be_visible()
    elif error == "maximum tables allowed":
        expect(context.page.get_by_text("Basic table: The maximum number of items is 1")).to_be_visible()
    elif error == "unselected options":
        expect(context.page.get_by_text("Select an option for Table headers")).to_be_visible()
    elif error == "empty table":
        expect(context.page.get_by_text("The table cannot be empty")).to_be_visible()


@when("the user publishes a page with example content")
def user_publishes_release_page_with_example_content(context: Context):
    click_add_child_page(context)
    user_enters_example_content_on_release_page(context)
    user_clicks_publish(context)


@then("the user cannot delete the release date change")
def user_cannot_delete_the_release_date_change(context: Context):
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    expect(
        page.locator("#panel-child-content-changes_to_release_date-section [data-streamfield-action='DELETE']")
    ).to_be_hidden()


@when('the user publishes a "Confirmed" page with example content')
def user_publishes_confirmed_release_page_with_example_content(context: Context):
    click_add_child_page(context)
    set_page_status(context, "Confirmed")
    user_enters_example_content_on_release_page(context)
    user_clicks_publish(context)


@when("the user adds {feature} under changes to release date")
def add_changes_to_release_date_info(context: Context, feature: str):
    page = context.page
    if feature == "multiple release date changes":
        add_feature(context, "a release date change")
        add_changes_to_release_date_info(context, "another release date change")
    elif feature == "a release date change with no date change log":
        page.get_by_role("textbox", name="Release date*").fill("2025-01-25")

    elif feature == "a date change log but no release date change":
        add_feature(context, "a release date change")
    elif feature == "another release date change":
        change_to_release_date_section = page.locator("#panel-child-content-changes_to_release_date-section")
        change_to_release_date_section.get_by_role("button", name="Insert a block").nth(1).click()
        change_to_release_date_section.get_by_label("Previous date*").nth(1).fill("2024-12-19 12:15")
        change_to_release_date_section.get_by_label("Reason for change*").nth(1).fill("New update to release schedule")
    else:
        raise ValueError(f"Unsupported feature: {feature}")


@then("an error message is displayed to say the page could not be saved")
def error_page_not_saved(context: Context):
    expect(context.page.get_by_text("The page could not be saved due to validation errors")).to_be_visible()


@then("under changes to release date, the user sees a validation error message: {error}")
def error_invalid_changes_to_release_date(context: Context, error: str):
    if error == "multiple release date changes":
        expect(
            context.page.get_by_text("Only one 'Changes to release date' entry can be added per release date change.")
        ).to_be_visible()
    elif error == "release date change with no date change log":
        expect(
            context.page.get_by_text(
                "If a confirmed calendar entry needs to be rescheduled, the 'Changes to release date'"
                " field must be filled out."
            )
        ).to_be_visible()
    elif error == "date change log with no release date change":
        expect(
            context.page.get_by_text(
                "You have added a 'Changes to release date' entry, but the release date is the same"
                " as the published version."
            )
        ).to_be_visible()
    else:
        raise ValueError(f"Unsupported error: {error}")


@then("the release calendar page is successfully updated")
def release_calendar_page_is_successfully_updated(context: Context):
    page = context.page
    expect(page.get_by_text("Page 'My Release' has been updated.")).to_be_visible()


@then("the release calendar page is successfully published")
def release_calendar_page_is_successfully_published(context: Context):
    page = context.page
    expect(page.get_by_text("Page 'My Release' has been published.")).to_be_visible()
