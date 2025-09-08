from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.conf import settings
from django.urls import reverse
from playwright.sync_api import expect

from cms.articles.tests.factories import (
    ArticleSeriesPageFactory,
    StatisticalArticlePageFactory,
)
from cms.topics.tests.factories import TopicPageFactory


@given("a topic page exists under the homepage")
def the_user_creates_theme_and_topic_pages(context: Context) -> None:
    context.topic_page = TopicPageFactory(title="Public Sector Finance")


@given("the topic page has a statistical article in a series")
def the_topic_page_has_a_statistical_article_in_a_series(context: Context) -> None:
    context.article_series_page = ArticleSeriesPageFactory(title="PSF")
    context.first_statistical_article_page = StatisticalArticlePageFactory(parent=context.article_series_page)


@given("the user has featured the series")
def the_user_has_featured_the_series(context: Context) -> None:
    context.topic_page.featured_series = context.article_series_page
    context.topic_page.save_revision().publish()


@when("the user visits the topic page")
def visit_topic_page(context: Context) -> None:
    context.page.goto(f"{context.base_url}{context.topic_page.url}")


@when("the user selects the article series")
def the_user_select_article_series(context: Context) -> None:
    context.page.get_by_role("link", name=context.article_series_page.title, exact=True).click()


@step("the user edits the ancestor topic")
def user_edits_the_ancestor_topic(context: Context) -> None:
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.topic_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the user views the topic page")
def user_views_the_topic_page(context: Context) -> None:
    context.page.goto(f"{context.base_url}{context.topic_page.url}")


@step("the user clicks to add headline figures to the topic page")
def user_clicks_to_add_headline_figures_to_the_topic_page(context: Context, *, button_index: int = 0) -> None:
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Insert a block").nth(button_index).click()
    page.wait_for_timeout(100)
    panel.get_by_role("button", name="Choose Article Series page and headline figure").click()
    page.wait_for_timeout(100)  # Wait for modal to open


@step("the user adds two headline figures to the topic page")
def user_adds_two_headline_figures_to_the_topic_page(context: Context) -> None:
    page = context.page
    user_clicks_to_add_headline_figures_to_the_topic_page(context)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(0).click()
    user_clicks_to_add_headline_figures_to_the_topic_page(context, button_index=1)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(1).click()


@step("the user reorders the headline figures on the topic page")
def user_reorders_the_headline_figures_on_the_topic_page(context: Context) -> None:
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Move up").nth(1).click()


@then("the topic page with the example content is displayed")
def the_topic_page_with_example_content(context: Context) -> None:
    expect(context.page.get_by_role("heading", name=context.topic_page.title)).to_be_visible()


@then("the user can see the topic page featured article")
def user_sees_featured_article(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Featured")).to_be_visible()
    expect(context.page.get_by_text(context.first_statistical_article_page.display_title)).to_be_visible()
    expect(context.page.get_by_text(context.first_statistical_article_page.main_points_summary)).to_be_visible()


@then("the user can see the newly created article in featured spot")
def user_sees_newly_featured_article(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Featured")).to_be_visible()
    expect(
        context.page.locator("#featured").get_by_text(context.new_statistical_article_page.display_title)
    ).to_be_visible()
    expect(
        context.page.locator("#featured").get_by_text(context.new_statistical_article_page.main_points_summary)
    ).to_be_visible()


@then("the published topic page has the added headline figures in the correct order")
def the_published_topic_page_has_the_added_headline_figures_in_the_correct_order(
    context: Context,
) -> None:
    page = context.page
    headline_block = page.locator("#headline-figures .ons-grid__col")
    expect(headline_block.nth(0).get_by_text("First headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("Second headline figure")).to_be_visible()


@then("the published topic page has reordered headline figures")
def the_published_topic_page_has_reordered_headline_figures(context: Context) -> None:
    page = context.page
    headline_block = page.locator("#headline-figures .ons-grid__col")
    expect(headline_block.nth(0).get_by_text("Second headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("First headline figure")).to_be_visible()


@then("the headline figures on the topic page link to the statistical page")
def the_headline_figures_on_the_topic_page_link_to_the_statistical_page(
    context: Context,
) -> None:
    page = context.page
    page.get_by_text("First headline figure").click()
    expect(page.get_by_role("heading", name="The article page")).to_be_visible()
    page.go_back()
    page.get_by_text("Second headline figure").click()
    expect(page.get_by_role("heading", name="The article page")).to_be_visible()


@when("the user adds a time series page link")
def the_user_adds_a_time_series_page_link(context: Context) -> None:
    page = context.page
    page.locator("#panel-child-content-time_series-content").get_by_role("button", name="Insert a block").click()
    page.get_by_role("region", name="Time series page link").get_by_label("Title*").fill("Page title")
    page.get_by_role("textbox", name="Url*").fill(settings.ONS_WEBSITE_BASE_URL + "/time-series/")
    page.get_by_role("textbox", name="Description*").fill("Page summary for time series example")


@then("the time series section is displayed on the page")
def the_time_series_page_link_is_displayed_on_the_page(context: Context) -> None:
    page = context.page

    expect(
        page.locator("#time-series").get_by_role("heading", name="Time Series", exact=True)
    ).to_be_visible()  # Section heading
    expect(page.locator("#time-series").get_by_role("link", name="Page title")).to_be_visible()
    expect(page.locator("#time-series").get_by_text("Time series", exact=True)).to_be_visible()  # Content type label
    expect(page.locator("#time-series").get_by_text("Summary")).to_be_visible()


@then("the time series item appears in the table of contents")
def the_time_series_item_appears_in_the_table_of_contents(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Time Series")).to_be_visible()
