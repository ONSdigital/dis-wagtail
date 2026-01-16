"""Step definitions for topic page creation and configuration tests."""

from behave import then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@when("the user fills in the topic page title")
def user_fills_in_topic_page_title(context: Context) -> None:
    """Fill in only the title field of the topic page."""
    context.page.get_by_role("textbox", name="Title*").fill("Test Title")


@when("the user fills in the topic page summary")
def user_fills_in_topic_page_summary(context: Context) -> None:
    """Fill in only the summary field of the topic page."""
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Test Summary")


@when("the user selects the taxonomy topic")
def user_selects_taxonomy_topic(context: Context) -> None:
    """Select the existing taxonomy topic for the page."""
    context.page.get_by_role("tab", name="Taxonomy").click()
    context.page.get_by_role("button", name="Choose a topic").click()
    context.page.wait_for_timeout(250)
    context.page.get_by_role("link", name=context.existing_topic.title).click()


@then('the user sees the success message "{message}"')
def user_sees_success_message(context: Context, message: str) -> None:
    """Assert the success message is visible."""
    expect(context.page.get_by_text(message)).to_be_visible()


@then('the user sees the validation error "{error_message}"')
def user_sees_validation_error(context: Context, error_message: str) -> None:
    """Assert the validation error is visible."""
    expect(context.page.get_by_text(error_message).first).to_be_visible()


@then('the user sees the validation error "{error_message}" in the summary field')
def user_sees_validation_error_in_summary(context: Context, error_message: str) -> None:
    """Assert the validation error is visible near the summary field."""
    summary_region = context.page.get_by_role("region", name="Summary*")
    # Go up to the parent of the summary region to find the error message
    expect(summary_region.locator("..").get_by_text(error_message)).to_be_visible()


@then("the user sees the taxonomy validation error")
def user_sees_taxonomy_validation_error(context: Context) -> None:
    """Assert the taxonomy validation error is visible."""
    context.page.get_by_role("tab", name="Taxonomy").click()
    expect(context.page.get_by_text("A topic is required")).to_be_visible()


@then("the user does not see headline figure validation errors")
def user_does_not_see_headline_figure_errors(context: Context) -> None:
    """Assert no headline figure validation errors are visible."""
    expect(context.page.get_by_text("If you add headline figures, please add at least 2.")).not_to_be_visible()


@then("the user sees the draft saved message")
def user_sees_draft_saved_message(context: Context) -> None:
    """Assert the draft saved message is visible."""
    # Wait for the page to process the save
    context.page.wait_for_timeout(500)
    expect(context.page.get_by_text("Page 'Test Title' created.")).to_be_visible()


@then("the user can continue editing the page")
def user_can_continue_editing(context: Context) -> None:
    """Assert the user can continue editing the page."""
    # Check that the title field and save button are still visible
    expect(context.page.get_by_role("textbox", name="Title*")).to_be_visible()
    expect(context.page.get_by_role("button", name="Save draft")).to_be_visible()


@when("the user adds an external related article without a title")
def user_adds_external_article_without_title(context: Context) -> None:
    """Add an external related article without filling in the title."""
    context.page.get_by_role("button", name="Add topic page related article").click()
    context.page.locator("#id_related_articles-0-external_url").fill("https://example.com/test")


@when("the user adds an empty related article")
def user_adds_empty_related_article(context: Context) -> None:
    """Add a related article without selecting a page or providing an external URL."""
    context.page.get_by_role("button", name="Add topic page related article").click()


@when("the user adds a time series link with an invalid URL")
def user_adds_time_series_with_invalid_url(context: Context) -> None:
    """Add a time series link with an invalid (non-ONS) URL."""
    page = context.page
    panel = page.locator("#panel-child-content-time_series-content")
    panel.get_by_role("button", name="Insert a block").click()
    page.get_by_role("region", name="Time series page link").get_by_label("Title*").fill("Invalid Time Series")
    page.get_by_role("textbox", name="Url*").fill("https://invalid-domain.com/timeseries")
    page.get_by_role("textbox", name="Description*").fill("Invalid time series")


@then("the user sees the time series URL validation error")
def user_sees_time_series_url_error(context: Context) -> None:
    """Assert the time series URL validation error is visible."""
    expect(context.page.get_by_text("The URL hostname is not in the list of allowed domains")).to_be_visible()


@then("the topic page preview displays the page title and summary")
def topic_page_preview_displays_content(context: Context) -> None:
    """Assert the topic page preview shows the page title and summary."""
    # Wait for the preview iframe to load
    context.page.wait_for_timeout(1000)

    iframe_locator = context.page.frame_locator("#w-preview-iframe")

    # context.topic_page is set by the "a topic page exists under the homepage" step
    expect(iframe_locator.get_by_role("heading", name=context.topic_page.title)).to_be_visible(timeout=10000)
    expect(iframe_locator.get_by_text(context.topic_page.summary)).to_be_visible()
