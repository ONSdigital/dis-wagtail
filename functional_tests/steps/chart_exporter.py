# pylint: disable=not-callable
import re

from behave import given, then
from behave.runner import Context
from playwright.sync_api import Locator, Page, expect

from cms.datavis.tests.chart_exporter_mock import PNG

DOWNLOAD_IMAGE = re.compile(r"^Download image")


def open_chart_downloads(page: Page) -> Locator:
    """Open the chart's download menu, once the design system's JavaScript has initialised it."""
    download_details = page.locator('.ons-js-details[id^="figure-downloads--"]')
    expect(download_details).to_contain_class("ons-details--initialised")
    download_details.get_by_text("Download: line chart").click()
    return download_details


@given('the chart exporter responds with "{scenario}"')
def the_chart_exporter_responds_with(context: Context, scenario: str) -> None:
    context.chart_exporter.set_default(scenario)


@then("the chart image can be downloaded")
def the_chart_image_can_be_downloaded(context: Context) -> None:
    image_link = open_chart_downloads(context.page).get_by_role("link", name=DOWNLOAD_IMAGE)
    expect(image_link).to_be_visible()
    href = image_link.get_attribute("href")

    # page.request shares the browser's cookies, so this is fetched as the logged-in user
    response = context.page.request.get(f"{context.base_url}{href}")
    expect(response).to_be_ok()
    assert response.headers["content-type"] == "image/png"
    assert response.body() == PNG


@then("the chart has no image download link")
def the_chart_has_no_image_download_link(context: Context) -> None:
    download_details = open_chart_downloads(context.page)
    expect(download_details.get_by_role("link", name="Download CSV")).to_be_visible()
    expect(download_details.get_by_role("link", name=DOWNLOAD_IMAGE)).to_have_count(0)


@then('the chart exporter was asked to render the "{title}" chart')
def the_chart_exporter_was_asked_to_render_the_chart(context: Context, title: str) -> None:
    requests = context.chart_exporter.requests
    assert requests, "The chart exporter received no requests"
    for request in requests:
        assert (request.method, request.path) == ("POST", "/charts"), f"Unexpected request: {request}"
        assert request.body["chart_config"]["title"] == title
