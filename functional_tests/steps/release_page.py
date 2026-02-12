# pylint: disable=not-callable
import datetime
from datetime import timedelta

from behave import given, step, then, when
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect
from wagtail.models import Revision

from cms.core.custom_date_format import ons_default_datetime
from cms.release_calendar.tests.factories import ReleaseCalendarPageFactory
from functional_tests.step_helpers.release_page_helpers import (
    add_feature,
    display_feature_in_preview_tab,
    get_status_from_string,
    handle_changes_to_release_date_feature,
    handle_pre_release_access_feature,
    handle_release_calendar_page_errors,
)
from functional_tests.steps.page_editor import user_clicks_publish


@given("a release calendar page exists")
def a_release_calendar_page_exists(context: Context) -> Revision:
    context.release_calendar_page = ReleaseCalendarPageFactory()
    return context.release_calendar_page.save_revision()


@given("a sample release calendar page exists")
def a_sample_release_calendar_page_exists(context: Context) -> Revision:
    context.release_calendar_page = ReleaseCalendarPageFactory(
        title="My Release",
        release_date=datetime.datetime(year=2024, month=12, day=25, hour=9, minute=30),
        summary="My example release page",
        is_accredited=True,
        contact_details=context.contact_details_snippet,
    )
    context.release_calendar_page.content = [
        {
            "type": "release_content",
            "value": {
                "title": "My Example Content Link",
                "links": [{"page": context.release_calendar_page.get_parent().pk}],
            },
        }
    ]
    return context.release_calendar_page.save_revision()


@given('a "{status_str}" published release calendar page exists')
def a_published_release_calendar_page_exists(context: Context, status_str: str) -> None:
    a_sample_release_calendar_page_exists(context)
    context.release_calendar_page.status = get_status_from_string(status_str)
    context.release_calendar_page.save_revision().publish()


@given('a "{status_str}" published release calendar page with a date change log exists')
def a_release_calendar_page_with_date_change_log_exists(context: Context, status_str: str) -> None:
    context.release_calendar_page = ReleaseCalendarPageFactory(status=get_status_from_string(status_str))
    context.release_calendar_page.save_revision().publish()
    release_date = context.release_calendar_page.release_date
    context.release_calendar_page.release_date = release_date + timedelta(days=1)
    context.release_calendar_page.changes_to_release_date = [
        {
            "type": "date_change_log",
            "value": {"previous_date": release_date, "reason_for_change": "The reason"},
        }
    ]
    context.release_calendar_page.save_revision().publish()


@given("the user navigates to the release calendar page")
def navigate_to_release_calendar_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="View child pages of 'Home'").first.click()
    context.page.get_by_role("link", name="Release calendar", exact=True).click()


@when("the user publishes a page with example content")
def user_publishes_release_page_with_example_content(context: Context) -> None:
    click_add_child_page(context)
    user_enters_example_content_on_release_page(context)
    user_clicks_publish(context)


@given("a Release Calendar page with a published notice exists")
def create_release_calendar_page(context: Context) -> None:
    context.release_calendar_page = ReleaseCalendarPageFactory(
        notice="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    )
    context.release_calendar_page.save_revision().publish()


@when('the user clicks "Add child page" to create a new draft release calendar page')
def click_add_child_page(context: Context) -> None:
    context.page.get_by_label("Add child page").click()


@then("today's date and 9:30 AM are set as the default in the release date input field")
def default_release_date_time_is_displayed(context: Context) -> None:
    default_datetime = ons_default_datetime().strftime("%Y-%m-%d %H:%M")
    expect(context.page.locator("#id_release_date")).to_have_value(default_datetime)


@step('the datetime placeholder, "{time}", is displayed in the release date input field')
def datetime_placeholder_is_displayed_in_release_page_date_input_fields(context: Context, time: str) -> None:
    expect(context.page.locator("#id_release_date")).to_have_attribute("placeholder", time)
    expect(context.page.locator("#id_next_release_date")).to_have_attribute("placeholder", time)


@then("the time selection dropdown displays options in 30-minute intervals")
def thirty_minute_interval_for_time_selection(context: Context) -> None:
    time_picker = context.page.locator(".xdsoft_timepicker")
    context.page.get_by_role("textbox", name="Release date*").click()
    hours = [f"{h:02}" for h in range(24)]

    for hour in hours:
        expect(time_picker.get_by_text(f"{hour}:00").nth(2)).to_be_visible()
        expect(time_picker.get_by_text(f"{hour}:30").first).to_be_visible()

    context.page.get_by_role("textbox", name="Next release date", exact=True).click()
    for hour in hours:
        expect(time_picker.get_by_text(f"{hour}:00").nth(3)).to_be_visible()
        expect(time_picker.get_by_text(f"{hour}:30").nth(1)).to_be_visible()


@when('the user enters "{page_status}" page content')
@when("the user enters some example content on the page")
def user_enters_example_content_on_release_page(context: Context, page_status: str | None = None) -> None:
    if page_status == "Cancelled":
        context.page.locator(".public-DraftStyleDefault-block").first.fill("Notice cancelled")

    context.page.get_by_placeholder("Page title*").fill("My Release")

    context.page.get_by_role("textbox", name="Release date*").fill("2024-12-25 09:30")

    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My example release page")

    context.page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("region", name="Release content").get_by_label("Title*").fill("My Example Content Link")

    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_label("Explore").click()
    context.page.get_by_role("link", name="Release calendar").click()

    context.page.get_by_label("Accredited Official Statistics").check()

    context.page.get_by_role("button", name="Choose contact details").click()
    context.page.get_by_role("link", name=context.contact_details_snippet.name).click()


@when("the user inputs a {meridiem_indicator} datetime")
def add_datetime(context: Context, meridiem_indicator: str) -> None:
    valid_times = {
        "am": "2025-03-01 10:00",
        "pm": "2025-03-01 17:00",
    }
    try:
        value = valid_times[meridiem_indicator]
    except KeyError as exc:
        raise ValueError(f"Unsupported MeridiemIndicator: {meridiem_indicator}") from exc
    context.page.get_by_role("textbox", name="Release date*").fill(value)


@then('the datetime is displayed with "{meridiem_indicator}"')
def display_datetime_with_meridiem(context: Context, meridiem_indicator: str) -> None:
    expected_texts = {
        "am": "March 2025 10:00am",
        "pm": "March 2025 5:00pm",
    }
    try:
        expected = expected_texts[meridiem_indicator]
    except KeyError as exc:
        raise ValueError(f"Unsupported MeridiemIndicator: {meridiem_indicator}") from exc
    expect(context.page.get_by_text(expected)).to_be_visible()


@step('the user sets the page status to "{page_status}"')
def set_page_status(context: Context, page_status: str) -> None:
    context.page.get_by_label("Status*").select_option(page_status.upper())


# Combined step definition for both page status and preview mode display
@then('the "{status_or_mode}" page is displayed')
@then('the "{status_or_mode}" page is displayed in the preview tab')
def display_release_page_by_status_or_mode(context: Context, status_or_mode: str) -> None:
    match status_or_mode:
        case "Provisional" | "Confirmed":
            expect(context.page.get_by_text("This release is not yet published")).to_be_visible()
        case "Cancelled":
            expect(context.page.get_by_text("Cancelled", exact=True)).to_be_visible()
            expect(context.page.get_by_text("Notice cancelled")).to_be_visible()
        case "Published":
            display_example_content_release_page_in_preview_tab(context)
        case _:
            raise ValueError(f"Unsupported status or mode: {status_or_mode}")


@step("the user adds {feature} to the release calendar page")
def add_feature_to_release_calendar_page(context: Context, feature: str) -> None:
    add_feature(context.page, feature)


@then("the example content is displayed in the preview tab")
def display_example_content_release_page_in_preview_tab(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="My Release")).to_be_visible()
    expect(context.page.get_by_role("heading", name="My Example Content Link")).to_be_visible()
    expect(
        context.page.locator("#my-example-content-link").get_by_role("link", name="Release calendar")
    ).to_be_visible()
    expect(context.page.get_by_role("heading", name="Contact details")).to_be_visible()
    expect(context.page.get_by_text(context.contact_details_snippet.name)).to_be_visible()
    expect(context.page.get_by_role("link", name=context.contact_details_snippet.email)).to_be_visible()
    expect(context.page.get_by_text("Accredited Official Statistics", exact=True)).to_be_visible()


@then("{feature} is displayed in the release calendar page preview tab")
def display_features_in_preview_tab(context: Context, feature: str) -> None:
    display_feature_in_preview_tab(context.page, feature)


@then('the page status is set to "Provisional" and the release date text field is visible')
def check_that_default_status_is_provisional_and_release_date_text_is_visible(
    context: Context,
) -> None:
    expect(context.page.get_by_label("Status*")).to_have_value("PROVISIONAL")
    expect(context.page.get_by_text("Or, release date text")).to_be_visible()


@then("the date text field is not visible")
def check_date_text_field(context: Context) -> None:
    expect(context.page.get_by_text("Or, release date text")).not_to_be_visible()


@then("an error message is displayed to say the page could not be created")
def error_page_not_created(context: Context) -> None:
    expect(context.page.get_by_text("The page could not be created due to validation errors")).to_be_visible()


@then("the user sees a validation error message: {error}")
def error_invalid_release_calendar_page_input(context: Context, error: str) -> None:
    handle_release_calendar_page_errors(context.page, error)


@then("the notice field is disabled")
def check_notice_field_disabled(context: Context) -> None:
    expect(context.page.locator('[name="notice"]')).to_be_disabled()


@when("the user navigates to the published release calendar page")
def navigate_to_published_release_calendar_page(context: Context) -> None:
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.release_calendar_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@when("{feature} added under pre-release access")
def pre_release_access_info(context: Context, feature: str) -> None:
    handle_pre_release_access_feature(context.page, feature)


@when("the user changes the release date to a new date")
def user_changes_release_date_to_new_date(context: Context) -> None:
    context.page.get_by_role("textbox", name="Release date*").fill("2024-12-21 15:00")


@when("the user changes the release date to a new date again")
def user_changes_release_date_to_new_date_again(context: Context) -> None:
    context.page.get_by_role("textbox", name="Release date*").fill("2025-01-21 15:00")


@then("the previous date field is pre-populated with the old release date")
def previous_release_date_field_is_pre_populated(context: Context) -> None:
    changes_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    expect(changes_to_release_date_section.get_by_label("Previous date*")).to_have_value("2024-12-25 09:30")


@then("the Changes to release date block is not visible")
def previous_release_date_in_date_change_block_is_empty(context: Context) -> None:
    expect(context.page.locator("#panel-child-content-changes_to_release_date-section")).not_to_be_visible()


@then("the previous release date field is not editable")
def previous_release_date_field_is_not_editable(context: Context) -> None:
    changes_to_release_date_section = context.page.locator("#panel-child-content-changes_to_release_date-section")
    expect(changes_to_release_date_section.get_by_label("Previous date*")).not_to_be_editable()


@then("the user cannot delete the date change log")
def user_cannot_delete_the_release_date_change(context: Context) -> None:
    context.page.wait_for_timeout(500)  # added to allow JS to be ready
    expect(
        context.page.locator("#panel-child-content-changes_to_release_date-section [data-streamfield-action='DELETE']")
    ).to_be_hidden()


@then("an error message is displayed to say the page could not be saved")
def error_page_not_saved(context: Context) -> None:
    expect(context.page.get_by_text("The page could not be saved due to validation errors")).to_be_visible()


@when("the user adds {feature} under changes to release date")
def add_changes_to_release_date_info(context: Context, feature: str) -> None:
    handle_changes_to_release_date_feature(context.page, feature)


@when('the user publishes a "Confirmed" page with example content')
def user_publishes_confirmed_release_page_with_example_content(
    context: Context,
) -> None:
    click_add_child_page(context)
    set_page_status(context, "Confirmed")
    user_enters_example_content_on_release_page(context)
    user_clicks_publish(context)
