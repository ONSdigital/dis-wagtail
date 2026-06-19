# pylint: disable=not-callable
from behave import then, when
from behave.runner import Context
from playwright.sync_api import expect


@when("the unsaved controller gets it's initial snapshot")
def unsaved_controller_has_time_to_generate_snapshot(context: Context) -> None:
    # The Wagtail UnsavedController waits 2000ms after page load before taking its
    # initial form snapshot. Playwright's fill() is very fast so we need to wait
    # until the snapshot is taken before making edits.
    context.page.wait_for_timeout(2100)


@when("the user types content into the information page editor")
def user_types_autosave_content(context: Context) -> None:
    context.autosave_title = "Autosave Test Page"
    context.autosave_summary = "This content should be autosaved"

    context.page.get_by_role("textbox", name="Title*").fill(context.autosave_title)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill(context.autosave_summary)


@when("the user waits the autosave interval")
def wait_for_autosave_interval(context: Context) -> None:
    # Wait for the autosave POST request to complete.
    # This is more reliable than a fixed timeout based on settings.WAGTAIL_AUTOSAVE_INTERVAL,
    # which is 0 in functional test settings and may not reflect the active override.
    with context.page.expect_response(
        lambda response: response.request.method == "POST"
        and "application/json" in response.request.headers.get("accept", "")
        and "/edit" in response.request.url,
        timeout=10_000,
    ):
        pass


@then("the typed content is preserved in the editor")
def autosaved_content_is_preserved(context: Context) -> None:
    expect(context.page.get_by_role("textbox", name="Title*")).to_have_value(context.autosave_title)
    expect(context.page.get_by_role("region", name="Summary*")).to_contain_text(context.autosave_summary)
