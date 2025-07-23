from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.core.custom_date_format import ons_default_datetime

# Time input features


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


@when("the user adds an invalid release date text")
def user_inputs_invalid_release_date_text(context: Context):
    context.page.get_by_label("Or, release date text").fill("Invalid 4356")


@when("the user adds an invalid next release date text")
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
def user_adds_next_release_date_before_release_date(context: Context):
    context.page.get_by_role("textbox", name="Release date*").fill("2024-12-25")
    context.page.locator("#id_next_release_date").fill("2023-12-25")


@when("the user enters both next release date and next release date text")
def user_adds_both_next_and_release_date(context: Context):
    context.page.locator("#id_next_release_date").fill("2025-12-25")
    context.page.locator("#id_next_release_date_text").fill("December 2025")


@then("an error message says you cannot enter a next release date and a next release date text at the same time")
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
