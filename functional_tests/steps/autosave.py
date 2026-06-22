# pylint: disable=not-callable
from behave import then, when
from behave.runner import Context
from playwright.sync_api import Locator, expect


def _fill_and_wait_for_autosave(context: Context, locator: Locator, value: str) -> None:
    """Fill *locator* with *value* and block until the resulting autosave POST completes.

    The response watcher is registered before ``fill()`` is called so it cannot miss a
    save that fires during Playwright's slow_mo delay.
    """
    with context.page.expect_response(
        lambda response: response.request.method == "POST"
        and "application/json" in response.request.headers.get("accept", "")
        and "/edit" in response.request.url,
        timeout=15_000,
    ):
        locator.fill(value)


@when("the unsaved controller gets it's initial snapshot")
def unsaved_controller_has_time_to_generate_snapshot(context: Context) -> None:
    # The Wagtail UnsavedController waits 2000ms after page load before taking its
    # initial form snapshot. Playwright's fill() is very fast so we need to wait
    # until the snapshot is taken before making edits.
    context.page.wait_for_timeout(2100)


@when("the user types content into the information page title")
def user_types_autosave_title(context: Context) -> None:
    context.autosave_title = "Autosave Test Page"
    _fill_and_wait_for_autosave(
        context,
        context.page.get_by_role("textbox", name="Title*"),
        context.autosave_title,
    )


@when("the user types content into the information page summary")
def user_types_autosave_summary(context: Context) -> None:
    context.autosave_summary = "This content should be autosaved"
    _fill_and_wait_for_autosave(
        context,
        context.page.get_by_role("region", name="Summary*").get_by_role("textbox"),
        context.autosave_summary,
    )


@then("the typed content is preserved in the editor")
def autosaved_content_is_preserved(context: Context) -> None:
    expect(context.page.get_by_role("textbox", name="Title*")).to_have_value(context.autosave_title)
    expect(context.page.get_by_role("region", name="Summary*")).to_contain_text(context.autosave_summary)
