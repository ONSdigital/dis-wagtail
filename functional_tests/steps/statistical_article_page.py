from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.articles.tests.factories import ArticleSeriesPageFactory


@given("an article series page exists")
def the_topic_page_has_a_statistical_article_in_a_series(context: Context):
    context.article_series = ArticleSeriesPageFactory(title="PSF")


@when("the user goes to add a new statistical article page")
def user_goes_to_add_new_article_page(context: Context):
    if not getattr(context, "article_series", None):
        the_topic_page_has_a_statistical_article_in_a_series(context)

    add_url = reverse("wagtailadmin_pages:add", args=("articles", "statisticalarticlepage", context.article_series.pk))
    context.page.goto(f"{context.base_url}{add_url}")


@step("the user adds basic statistical article page content")
def user_populates_the_statistical_article_page(context: Context):
    page = context.page
    page.get_by_placeholder("Page title*").fill("The article page")
    page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Page summary")
    page.locator('[data-contentpath="main_points_summary"]').get_by_role("textbox").fill("Main points summary")

    page.get_by_label("Release date*").fill("2025-01-11")

    page.wait_for_timeout(50)  # added to allow JS to be ready
    page.locator("#panel-child-content-content-content").get_by_title("Insert a block").click()
    page.get_by_label("Section heading*").fill("Heading")
    page.locator("#panel-child-content-content-content").get_by_role("region").get_by_role(
        "button", name="Insert a block"
    ).click()
    page.get_by_text("Rich text").click()
    page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Content")


@step("the user adds a table with pasted content")
def user_adds_table_with_pasted_content(context: Context):
    page = context.page
    page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").nth(2).click()
    page.get_by_text("Table").click()
    page.get_by_role("region", name="Table", exact=True).get_by_label("Title").fill("The table title")
    page.get_by_role("region", name="Table", exact=True).get_by_label("Caption").fill("The caption")

    tinymce = (
        page.get_by_role("region", name="Table", exact=True).locator('iframe[title="Rich Text Area"]').content_frame
    )
    tinymce.get_by_role("cell").nth(0).click()
    tinymce.get_by_role("cell").nth(0).fill("cell1")
    tinymce.get_by_role("cell").nth(1).fill("cell2")

    page.get_by_role("region", name="Table", exact=True).get_by_label("Source").fill("The source")
    page.get_by_role("region", name="Table", exact=True).get_by_role("textbox").nth(3).fill("some footnotes")


@then("the published statistical article page is displayed with the populated data")
def the_statistical_article_page_is_displayed_with_the_populated_data(context: Context):
    expect(context.page.get_by_text("Statistical article", exact=True)).to_be_visible()
    expect(context.page.get_by_role("heading", name="The article page")).to_be_visible()
    expect(context.page.get_by_text("Page summary")).to_be_visible()
    expect(context.page.get_by_text("11 January 2025", exact=True)).to_be_visible()
    expect(context.page.get_by_role("heading", name="Cite this analysis")).to_be_visible()

    expect(context.page.get_by_role("heading", name="Heading")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Content")).to_be_visible()


@then("the published statistical article page has the added table")
def _published_statistical_article_page_has_the_added_table(context: Context):
    expect(context.page.get_by_role("table")).to_be_visible()
    expect(context.page.get_by_text("cell1")).to_be_visible()
    expect(context.page.get_by_text("cell2")).to_be_visible()
