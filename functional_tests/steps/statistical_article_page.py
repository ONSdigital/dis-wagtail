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
    page.locator('[data-contentpath="main_points_summary"] [role="textbox"]').fill("Main points summary")

    page.get_by_label("Release date*").fill("2025-01-11")

    page.wait_for_timeout(50)  # added to allow JS to be ready
    page.locator("#panel-child-content-content-content").get_by_title("Insert a block").click()
    page.get_by_label("Section heading*").fill("Heading")
    page.locator("#panel-child-content-content-content").get_by_role("region").get_by_role(
        "button", name="Insert a block"
    ).click()
    page.get_by_text("Rich text").click()
    page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Content")
    page.wait_for_timeout(500)  # ensure that the rich text content is picked up


@step("the user updates the statistical article page content")
def user_updates_the_statistical_article_page_content(context: Context):
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Updated content")


@step('the user clicks on "View superseded version"')
def user_clicks_on_view_superseded_version(context: Context):
    page = context.page
    page.locator("#corrections-and-notices .ons-details__heading").click()
    page.get_by_role("link", name="View superseded version").click()


@step("the user adds a table with pasted content")
def user_adds_table_with_pasted_content(context: Context):
    page = context.page
    page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").nth(2).click()
    page.get_by_text("Table").last.click()
    page.locator('[data-contentpath="footnotes"] [role="textbox"]').fill("some footnotes")
    page.get_by_role("region", name="Table", exact=True).get_by_label("Title").fill("The table title")
    page.get_by_role("region", name="Table", exact=True).get_by_label("Caption").fill("The caption")
    page.get_by_role("region", name="Table", exact=True).get_by_label("Source").fill("The source")

    tinymce = (
        page.get_by_role("region", name="Table", exact=True).locator('iframe[title="Rich Text Area"]').content_frame
    )
    tinymce.get_by_role("cell").nth(0).click()
    tinymce.get_by_role("cell").nth(0).fill("cell1")
    tinymce.get_by_role("cell").nth(1).fill("cell2")

    page.locator('[data-contentpath="footnotes"] [role="textbox"]').scroll_into_view_if_needed()
    page.locator('[data-contentpath="footnotes"] [role="textbox"]').fill("some footnotes")


@then("the published statistical article page is displayed with the populated data")
def the_statistical_article_page_is_displayed_with_the_populated_data(context: Context):
    expect(context.page.get_by_text("Statistical article", exact=True)).to_be_visible()
    expect(context.page.get_by_role("heading", name="The article page")).to_be_visible()
    expect(context.page.get_by_text("Page summary")).to_be_visible()
    expect(context.page.get_by_text("11 January 2025", exact=True)).to_be_visible()
    expect(context.page.get_by_role("heading", name="Cite this analysis")).to_be_visible()

    expect(context.page.get_by_role("heading", name="Heading")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Content")).to_be_visible()


@then("the published statistical article page is displayed with the updated data")
def the_statistical_article_page_is_displayed_with_the_updated_data(context: Context):
    expect(context.page.get_by_text("Updated content")).to_be_visible()


@then("the user can view the superseeded statistical article page")
def user_can_view_the_superseeded_statistical_article_page(context: Context):
    expect(context.page.get_by_role("heading", name="The article page")).to_be_visible()
    expect(context.page.get_by_text("Content", exact=True)).to_be_visible()


@step("the user returns to editing the statistical article page")
def user_returns_to_editing_the_statistical_article_page(context: Context):
    context.page.get_by_role("link", name="PSF: The article page", exact=True).click()


@then("the published statistical article page has the added table")
def the_published_statistical_article_page_has_the_added_table(context: Context):
    expect(context.page.get_by_role("table")).to_be_visible()
    expect(context.page.get_by_text("cell1")).to_be_visible()
    expect(context.page.get_by_text("cell2")).to_be_visible()


@then("the user can expand the footnotes")
def expand_footnotes(context: Context):
    page = context.page

    footnotes_content = page.get_by_text("some footnotes", exact=True)
    expect(page.get_by_role("link", name="Footnotes")).to_be_visible()
    expect(footnotes_content).to_be_hidden()

    page.get_by_role("link", name="Footnotes").click()
    expect(footnotes_content).to_be_visible()


@step("the user adds a correction")
def user_adds_a_correction(context: Context):
    page = context.page
    page.wait_for_timeout(500)
    page.locator("#tab-label-corrections_and_notices").click()
    page.locator("#panel-child-corrections_and_notices-corrections-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    page.get_by_label("When*").fill("2025-03-13 13:59")
    page.locator('[data-contentpath="text"] [role="textbox"]').fill("Correction text")
    page.wait_for_timeout(500)


@step("the user adds a notice")
def user_adds_a_notice(context: Context):
    page = context.page
    page.wait_for_timeout(500)
    page.locator("#tab-label-corrections_and_notices").click()
    page.locator("#panel-child-corrections_and_notices-notices-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    page.get_by_label("When*").fill("2025-03-13 13:59")
    page.locator('[data-contentpath="text"] [role="textbox"]').fill("Notice text")
    page.wait_for_timeout(500)


@then("the published statistical article page has the added correction")
def the_published_statistical_article_page_has_the_added_correction(context: Context):
    expect(context.page.get_by_role("link", name="Corrections ons-icon-chevron")).to_be_visible()
    expect(context.page.get_by_text("13 March 2025 1:59p.m.")).to_be_hidden()
    expect(context.page.get_by_text("Correction text")).to_be_hidden()


@then("the published statistical article page has the added notice")
def the_published_statistical_article_page_has_the_added_notice(context: Context):
    expect(context.page.get_by_role("link", name="Notices ons-icon-chevron")).to_be_visible()
    expect(context.page.get_by_text("13 March 2025 1:59p.m.")).to_be_hidden()
    expect(context.page.get_by_text("Notice text")).to_be_hidden()


@then("the user can edit the correction")
def user_cannot_edit_the_correction(context: Context):
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    page.locator("#tab-label-corrections_and_notices").click()
    expect(page.locator("#corrections-0-value-when")).to_be_editable()
    page.wait_for_timeout(50)  # added to prevent flakiness


@then("the user cannot delete the correction")
def user_cannot_delete_the_correction(context: Context):
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    page.locator("#tab-label-corrections_and_notices").click()
    expect(
        page.locator("#panel-child-corrections_and_notices-corrections-content [data-streamfield-action='DELETE']")
    ).to_be_hidden()
