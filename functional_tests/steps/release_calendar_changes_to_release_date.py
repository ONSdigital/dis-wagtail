from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

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


@when("the user edits this to have a different release date")
def user_enters_different_release_date(context: Context):
    context.page.get_by_role("textbox", name="Release date*").fill("2025-01-25")


@then("an error message is displayed describing that a date change log is needed")
def error_release_date_change_message(context: Context):
    expect(context.page.get_by_text("The page could not be saved")).to_be_visible()
    expect(context.page.get_by_text("If a confirmed calendar entry")).to_be_visible()
