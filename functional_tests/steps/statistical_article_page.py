# pylint: disable=not-callable
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from behave import given, step, then, when
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect
from wagtail_factories import ImageFactory

from cms.articles.tests.factories import (
    ArticleSeriesPageFactory,
    StatisticalArticlePageFactory,
)
from cms.datavis.tests.factories import TableDataFactory
from cms.topics.models import TopicPage
from functional_tests.step_helpers.utils import get_page_from_context

if TYPE_CHECKING:
    from wagtail.models import Revision


@given("an article series page exists")
def an_article_series_exists(context: Context) -> None:
    if topic_page := getattr(context, "topic_page", None):
        context.article_series_page = ArticleSeriesPageFactory(title="PSF", parent=topic_page)
    else:
        context.article_series_page = ArticleSeriesPageFactory(title="PSF")
        context.topic_page = TopicPage.objects.ancestor_of(context.article_series_page).first()


@given("a statistical article exists")
@given("the user has created a statistical article in a series")
@given("a statistical article page has been published under the topic page")
def a_statistical_article_exists(context: Context) -> Revision:
    an_article_series_exists(context)
    context.statistical_article_page = StatisticalArticlePageFactory(
        parent=context.article_series_page, news_headline=""
    )
    context.original_statistical_article_page_title = context.statistical_article_page.title
    return context.statistical_article_page.save_revision()


@given("a published statistical article exists")
def a_published_statistical_article_exists(context: Context) -> None:
    a_statistical_article_exists(context)
    context.statistical_article_page.content = [
        {"type": "section", "value": {"title": "Content", "content": [{"type": "rich_text", "value": "text"}]}}
    ]
    context.statistical_article_page.save_revision().publish()


@given("a statistical article page with headline figures exists")
def a_statistical_article_page_with_headline_figures_exists(context: Context) -> Revision:
    a_statistical_article_exists(context)
    context.statistical_article_page.headline_figures = [
        (
            "figure",
            {
                "figure_id": "figure_1",
                "title": "First headline figure",
                "figure": "~123%",
                "supporting_text": "First supporting text",
            },
        ),
        (
            "figure",
            {
                "figure_id": "figure_2",
                "title": "Second headline figure",
                "figure": "~321%",
                "supporting_text": "Second supporting text",
            },
        ),
    ]
    context.statistical_article_page.headline_figures_figure_ids = "figure_1,figure_2"
    return context.statistical_article_page.save_revision()


@given("a published statistical article page with headline figures exists")
def a_published_statistical_article_page_with_headline_figures_exists(context: Context) -> None:
    revision = a_statistical_article_page_with_headline_figures_exists(context)
    revision.publish()


@given("a published statistical article page with a correction exists")
def a_published_statistical_article_page_with_a_correction_exists(context: Context):
    revision = a_statistical_article_exists(context)
    context.statistical_article_page.content = [
        {"type": "section", "value": {"title": "Content", "content": [{"type": "rich_text", "value": "text"}]}}
    ]
    context.statistical_article_page.corrections = [
        (
            "correction",
            {
                "version_id": 1,
                "previous_version": revision.id,
                "when": "2025-03-13 13:59",
                "frozen": True,
                "text": "First correction text",
            },
        )
    ]
    context.statistical_article_page.save_revision().publish()


@given("a statistical article page with equations exists")
def a_statistical_article_page_with_equations_exists(context: Context) -> None:
    an_article_series_exists(context)
    content = [
        {
            "type": "section",
            "value": {
                "heading": "Statistical article",
                "content": [
                    {
                        "type": "equation",
                        "value": {
                            "equation": "$$y = mx + b$$",
                            "svg": "<svg id='svgfallback'></svg>",
                        },
                    }
                ],
            },
        }
    ]
    context.statistical_article_page = StatisticalArticlePageFactory(
        parent=context.article_series_page,
        title="Statistical article with equations",
        content=content,
    )
    context.statistical_article_page.save()


@when("the user creates a new statistical article in the series")
def create_a_new_article_in_the_series(context: Context) -> None:
    old_article_release_date = context.statistical_article_page.release_date
    context.new_statistical_article_page = StatisticalArticlePageFactory(
        title="January 2025",
        release_date=old_article_release_date + timedelta(days=1),
        parent=context.article_series_page,
    )


@when("the user goes to add a new statistical article page")
def user_goes_to_add_new_article_page(context: Context) -> None:
    if not getattr(context, "article_series_page", None):
        an_article_series_exists(context)

    add_url = reverse(
        "wagtailadmin_pages:add",
        args=("articles", "statisticalarticlepage", context.article_series_page.pk),
    )
    context.page.goto(f"{context.base_url}{add_url}")


@step("the user adds basic statistical article page content")
def user_populates_the_statistical_article_page(context: Context) -> None:
    page = context.page
    page_title = "The article page"
    page.get_by_role("textbox", name="Release Edition").fill(page_title)
    context.original_statistical_article_page_title = page_title
    page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Page summary")
    page.locator('[data-contentpath="main_points_summary"] [role="textbox"]').fill("Main points summary")

    page.get_by_label("Release date*").fill("2025-01-11")

    page.wait_for_timeout(50)  # added to allow JS to be ready
    page.get_by_role("textbox", name="Release Edition").focus()  # focus up to prevent any overlap with the action menu
    page.locator("#panel-child-content-content-content").get_by_title("Insert a block").click()
    page.get_by_label("Section heading*").fill("Heading")
    page.locator("#panel-child-content-content-content").get_by_role("region").get_by_role(
        "button", name="Insert a block"
    ).click()
    page.get_by_text("Rich text").click()
    page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Content")
    page.wait_for_timeout(500)  # ensure that the rich text content is picked up


@step("the user updates the statistical article page content")
def user_updates_the_statistical_article_page_content(context: Context) -> None:
    context.page.get_by_role("textbox", name="Release Edition").fill("Updated article title")


@step('the user clicks on "View superseded version"')
def user_clicks_on_view_superseded_version(context: Context) -> None:
    page = context.page
    page.get_by_text("Show detail").click()
    page.get_by_role("link", name="View superseded version").click()


@step("the {page_str} has a chart")
def the_page_has_a_chart(context: Context, page_str: str):
    the_page = get_page_from_context(context, page_str)
    the_page.content = [
        {
            "type": "section",
            "value": {
                "content": [
                    {
                        "type": "line_chart",
                        "id": uuid.uuid4(),
                        "value": {
                            "annotations": [],
                            "audio_description": "desc",
                            "caption": "",
                            "footnotes": "This is a lovely footnote",
                            "options": [],
                            "show_legend": True,
                            "show_markers": False,
                            "subtitle": "subtitle",
                            "table": {
                                "table_data": '{"data": [["Foo","Bar"],["1234","1337"],["",""],["",""],["",""]]}',
                                "table_type": "table",
                            },
                            "theme": "primary",
                            "title": "line chart",
                            "x_axis": {"tick_interval_desktop": None, "tick_interval_mobile": None, "title": ""},
                            "y_axis": {
                                "custom_reference_line": None,
                                "end_on_tick": True,
                                "max": None,
                                "min": None,
                                "start_on_tick": True,
                                "tick_interval_desktop": None,
                                "tick_interval_mobile": None,
                                "title": "",
                            },
                        },
                    },
                ],
                "title": "section",
            },
        }
    ]
    the_page.save_revision()


@step("the user adds a chart to the content")
def user_adds_chart_to_content(context: Context) -> None:
    """Add a chart block to the article content section."""
    page = context.page
    page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").nth(2).click()
    page.get_by_text("Line chart").click()

    chart_region = page.get_by_role("region", name="Line chart")
    chart_region.get_by_role("textbox", name="Title*", exact=True).fill("Test Chart Title")
    chart_region.get_by_role("textbox", name="Subtitle*").fill("Test Chart Subtitle")
    chart_region.get_by_label("Audio description*").fill("This is the chart audio description")

    # Wait for the table editor to be ready and fill in chart data
    page.wait_for_timeout(500)


@step("the user adds a table with pasted content")
def user_adds_table_with_pasted_content(context: Context) -> None:
    page = context.page
    page.locator("#panel-child-content-content-content").get_by_role("button", name="Insert a block").nth(2).click()
    page.get_by_text("Table").last.click()
    page.locator('[data-contentpath="footnotes"] [role="textbox"]').fill("some footnotes")
    page.get_by_role("region", name="Table", exact=True).get_by_label("Title").fill("The table title")
    page.get_by_role("region", name="Table", exact=True).get_by_label("Sub-heading").fill("The caption")
    page.get_by_role("region", name="Table", exact=True).get_by_label("Source").fill("The source")

    tinymce = (
        page.get_by_role("region", name="Table", exact=True).locator('iframe[title="Rich Text Area"]').content_frame
    )
    tinymce.get_by_role("cell").nth(0).click()
    tinymce.get_by_role("cell").nth(0).fill("cell1")
    tinymce.get_by_role("cell").nth(1).fill("cell2")

    page.locator('[data-contentpath="footnotes"] [role="textbox"]').scroll_into_view_if_needed()
    page.locator('[data-contentpath="footnotes"] [role="textbox"]').fill("some footnotes")


def check_populated_data(locator):
    expect(locator.get_by_text("Statistical article", exact=True)).to_be_visible()
    expect(locator.get_by_role("heading", name="The article page")).to_be_visible()
    expect(locator.get_by_text("Page summary")).to_be_visible()
    expect(locator.get_by_text("11 January 2025", exact=True)).to_be_visible()
    expect(locator.get_by_role("heading", name="Cite this analysis")).to_be_visible()

    expect(locator.get_by_role("heading", name="Heading")).to_be_visible()
    expect(locator.get_by_role("heading", name="Content")).to_be_visible()


@then("the published statistical article page is displayed with the populated data")
def the_statistical_article_page_is_displayed_with_the_populated_data(
    context: Context,
) -> None:
    check_populated_data(context.page)


@step("the statistical article page preview contains the populated data")
def step_open_preview_pane(context: Context) -> None:
    iframe = context.page.frame_locator("#w-preview-iframe")
    check_populated_data(iframe)


@then("the user can view the superseded statistical article page")
def user_can_view_the_superseded_statistical_article_page(context: Context) -> None:
    expect(context.page.get_by_role("heading", name=context.original_statistical_article_page_title)).to_be_visible()
    expect(context.page.get_by_role("heading", name="Content", exact=True)).to_be_visible()


@step("the user returns to editing the statistical article page")
def user_returns_to_editing_the_statistical_article_page(context: Context) -> None:
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.article_series_page.get_latest().id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@then("the published statistical article page has the added table")
@then("the statistical article page draft has the added table")
def the_published_statistical_article_page_has_the_added_table(
    context: Context,
) -> None:
    expect(context.page.get_by_role("table")).to_be_visible()
    expect(context.page.get_by_text("cell1")).to_be_visible()
    expect(context.page.get_by_text("cell2")).to_be_visible()


@then("the user can expand the footnotes")
def expand_footnotes(context: Context) -> None:
    page = context.page

    footnotes_content = page.get_by_text("some footnotes", exact=True)
    footnotes_link = page.get_by_role("link", name="Footnotes")
    expect(footnotes_content).to_be_hidden()

    footnotes_link.click()
    expect(footnotes_content).to_be_visible()


@step("the user adds a correction")
def user_adds_a_correction(context: Context) -> None:
    page = context.page
    page.wait_for_timeout(500)
    page.locator("#tab-label-corrections_and_notices").click()
    page.locator("#panel-child-corrections_and_notices-corrections-content").get_by_role(
        "button", name="Insert a block"
    ).click()
    page.get_by_label("When*").fill("2025-03-13 13:59")
    page.locator('[data-contentpath="text"] [role="textbox"]').fill("Correction text")
    page.wait_for_timeout(500)


@step("the user adds headline figures")
def user_adds_headline_figures(context: Context) -> None:
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Insert a block").click()
    page.wait_for_timeout(100)
    panel.get_by_role("button", name="Insert a block").nth(1).click()
    page.wait_for_timeout(100)
    panel.get_by_label("Title*").nth(0).fill("First headline figure")
    panel.get_by_label("Figure*").nth(0).fill("~123%")
    panel.get_by_label("Supporting text*").nth(0).fill("First supporting text")
    panel.get_by_label("Title*").nth(1).fill("Second headline figure")
    panel.get_by_label("Figure*").nth(1).fill("~321%")
    panel.get_by_label("Supporting text*").nth(1).fill("Second supporting text")


@step("the user reorders the headline figures on the Statistical Article Page")
def user_reorders_the_headline_figures_on_the_statistical_article_page(
    context: Context,
) -> None:
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Move up").nth(1).click()


@step("the user adds another correction using the add button at the bottom")
def user_adds_a_correction_using_bottom_add_button(context: Context) -> None:
    page = context.page
    page.wait_for_timeout(500)
    page.locator("#tab-label-corrections_and_notices").click()
    block_area = page.locator(
        "#panel-child-corrections_and_notices-corrections-content [data-streamfield-stream-container]"
    )

    block_area.locator("div:last-child").get_by_role("button", name="Insert a block").click()
    block_area.locator("[name='corrections-1-id']+section").get_by_label("When*").fill("2025-03-14 13:59")
    block_area.locator("[name='corrections-1-id']+section").locator(
        '[data-contentpath="text"] [role="textbox"]'
    ).scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    block_area.locator("[name='corrections-1-id']+section").locator('[data-contentpath="text"] [role="textbox"]').fill(
        "Correction text"
    )
    page.wait_for_timeout(500)


@step("the user adds a notice")
def user_adds_a_notice(context: Context) -> None:
    page = context.page
    page.wait_for_timeout(500)
    page.locator("#tab-label-corrections_and_notices").click()
    block_area = page.locator(
        "#panel-child-corrections_and_notices-notices-content [data-streamfield-stream-container]"
    )
    block_area.get_by_role("button", name="Insert a block").click()
    block_area.get_by_label("When*").fill("2025-03-15 13:59")
    block_area.locator('[data-contentpath="text"] [role="textbox"]').fill("Notice text")
    page.wait_for_timeout(500)


@step("the user adds an accordion section with title and content")
def user_adds_accordion_section(context: Context) -> None:
    page = context.page
    # context.page.wait_for_timeout(250)
    page.wait_for_timeout(50)  # added to allow JS to be ready
    page.locator("#panel-child-content-content-content").get_by_title("Insert a block").click()
    page.get_by_label("Section heading*").fill("Heading")
    page.locator("#panel-child-content-content-content").get_by_role("region").get_by_role(
        "button", name="Insert a block"
    ).click()
    page.get_by_text("Accordion").click()
    page.get_by_label("Title*").fill("Test Accordion Section")
    page.wait_for_timeout(50)  # added to allow JS to be ready
    page.get_by_role("region", name="Content*").get_by_role("textbox").nth(2).fill("Test accordion content")
    context.page.wait_for_timeout(500)  # Wait for JS to process


@then("the published statistical article page has the added correction")
@then("the statistical article page draft has the added correction")
def the_published_statistical_article_page_has_the_added_correction(
    context: Context,
) -> None:
    expect(context.page.get_by_role("heading", name="Corrections")).to_be_visible()
    expect(context.page.get_by_text("13 March 2025")).to_be_hidden()
    expect(context.page.get_by_text("Correction text")).to_be_hidden()


@then("the published statistical article page has the added accordion section")
@then("the statistical article page draft has the added accordion section")
def the_published_statistical_article_page_has_the_added_accordion_section(
    context: Context,
) -> None:
    expect(context.page.get_by_role("heading", name="Test Accordion Section")).to_be_visible()
    expect(context.page.get_by_text("Test accordion content")).to_be_hidden()


@then("the user can expand and collapse the accordion section")
def user_can_expand_and_collapse_accordion_section(context: Context) -> None:
    expect(context.page.get_by_role("button", name="Show all")).to_be_visible()
    context.page.get_by_role("heading", name="Test Accordion Section").click()
    expect(context.page.get_by_role("button", name="Hide all")).to_be_visible()
    expect(context.page.get_by_text("Test accordion content")).to_be_visible()
    context.page.get_by_role("heading", name="Test Accordion Section").click()
    expect(context.page.get_by_text("Test accordion content")).to_be_hidden()
    context.page.get_by_role("button", name="Show all").click()
    expect(context.page.get_by_role("button", name="Hide all")).to_be_visible()
    expect(context.page.get_by_text("Test accordion content")).to_be_visible()


@then("the user can expand and collapse {block_type} details")
def user_can_click_on_view_detail_to_expand_block(context: Context, block_type: str) -> None:
    if block_type == "correction":
        text = "Correction text"
        date = "13 March 2025 1:59pm"
    else:
        text = "Notice text"
        date = "15 March 2025"

    context.page.get_by_text("Show detail").click()
    expect(context.page.get_by_text(text)).to_be_visible()
    expect(context.page.get_by_text(date)).to_be_visible()
    if block_type == "correction":
        expect(context.page.get_by_role("link", name="View superseded version")).to_be_visible()

    context.page.wait_for_timeout(500)
    context.page.get_by_text("Hide detail").click()
    context.page.wait_for_timeout(500)
    expect(context.page.get_by_text(text)).to_be_hidden()
    expect(context.page.get_by_text(date)).to_be_hidden()


@then("the statistical article page has the corrections and notices block")
def the_published_statistical_article_page_has_the_corrections_and_notices_block(
    context: Context,
) -> None:
    expect(context.page.get_by_role("heading", name="Corrections and notices")).to_be_visible()


@then("the published statistical article page has the added headline figures")
@then("the published topic page has the added headline figures")
@then("the headline figures are shown")
def the_published_statistical_article_page_has_the_added_headline_figures(
    context: Context,
) -> None:
    page = context.page
    expect(page.get_by_text("First headline figure")).to_be_visible()
    expect(page.get_by_text("~123%")).to_be_visible()
    expect(page.get_by_text("Second headline figure")).to_be_visible()
    expect(page.get_by_text("~321%")).to_be_visible()
    expect(page.get_by_text("First supporting text")).to_be_visible()
    expect(page.get_by_text("Second supporting text")).to_be_visible()


@then('the user can click on "Show detail" to expand the corrections and notices block')
def user_can_click_on_show_detail_to_expand_corrections_and_notices_block(
    context: Context,
) -> None:
    context.page.get_by_text("Show detail").click()
    expect(context.page.get_by_text("Notice text")).to_be_visible()
    expect(context.page.get_by_text("15 March 2025")).to_be_visible()

    expect(context.page.get_by_text("Correction text")).to_be_visible()
    expect(context.page.get_by_text("13 March 2025 1:59pm")).to_be_visible()
    expect(context.page.get_by_role("link", name="View superseded version")).to_be_visible()


@then('the user can click on "Hide detail" to collapse the corrections and notices block')
def user_can_click_on_hide_detail_to_collapse_corrections_and_notices_block(
    context: Context,
) -> None:
    context.page.get_by_text("Hide detail").click()

    expect(context.page.get_by_text("Notice text")).to_be_hidden()
    expect(context.page.get_by_text("15 March 2025")).to_be_hidden()

    expect(context.page.get_by_text("Correction text")).to_be_hidden()
    expect(context.page.get_by_text("13 March 2025 1:59pm")).to_be_hidden()


@then("the published statistical article page has corrections in chronological order")
def the_published_statistical_article_page_has_corrections_in_chronological_order(
    context: Context,
) -> None:
    expect(context.page.locator("#corrections div:first-child").get_by_text("14 March 2025 1:59pm")).to_be_hidden()
    expect(context.page.locator("#corrections div:nth-child(2)").get_by_text("13 March 2025 1:59pm")).to_be_hidden()


@then("the published statistical article page has the added notice")
@then("the statistical article page draft has the added notice")
def the_published_statistical_article_page_has_the_added_notice(
    context: Context,
) -> None:
    expect(context.page.get_by_role("heading", name="Notices")).to_be_visible()
    expect(context.page.get_by_text("15 March 2025")).to_be_hidden()
    expect(context.page.get_by_text("Notice text")).to_be_hidden()


@then("the user can edit the correction")
def user_cannot_edit_the_correction(context: Context) -> None:
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    page.locator("#tab-label-corrections_and_notices").click()
    expect(page.locator("#corrections-0-value-when")).to_be_editable()
    page.wait_for_timeout(50)  # added to prevent flakiness, as the test following this check would sometimes fail


@then("the user cannot delete the correction")
def user_cannot_delete_the_correction(context: Context) -> None:
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    page.locator("#tab-label-corrections_and_notices").click()
    expect(
        page.locator("#panel-child-corrections_and_notices-corrections-content [data-streamfield-action='DELETE']")
    ).to_be_hidden()


@when("the user navigates to the related data editor tab")
def user_navigates_to_related_data_tab(context: Context) -> None:
    context.page.get_by_role("tab", name="Related data").click()
    context.editor_tab = "related_data"


@when('the user clicks "View data used in this article" on the article page')
def user_clicks_view_data_used_in_article(context: Context) -> None:
    context.page.get_by_role("link", name="View data used in this article").click()


@then("the related data page for the article is shown")
def check_related_data_page_content(context: Context) -> None:
    page = context.page
    expect(page.get_by_role("heading", name="All data related to The article page")).to_be_visible()
    expect(page.get_by_role("link", name="Looked Up Dataset")).to_be_visible()
    expect(page.get_by_text("Example dataset for functional testing")).to_be_visible()
    expect(page.get_by_role("link", name="Manual Dataset")).to_be_visible()
    expect(page.get_by_text("Manually entered test dataset")).to_be_visible()


@step("the user switches to the Promote tab")
def user_switches_to_promote_tab(context: Context) -> None:
    promote_tab = context.page.locator("#tab-label-promote")
    promote_tab.click()


@then('the user sees a "Featured Chart" field')
def user_sees_a_featured_chart_field(context: Context) -> None:
    field = context.page.locator("#panel-child-promote-featured_chart-section")
    expect(field).to_be_visible()
    add_block_icon = context.page.locator("#panel-child-promote-featured_chart-content").get_by_title("Insert a block")
    expect(add_block_icon).to_be_visible()


@step('the user clicks "Line chart" in the featured chart streamfield block selector')
def user_clicks_line_chart_in_featured_chart_streamfield_block_selector(
    context: Context,
) -> None:
    featured_chart_content = context.page.locator("#panel-child-promote-featured_chart-content")
    featured_chart_content.get_by_title("Insert a block").click()
    featured_chart_content.get_by_text("Line chart").click()


@step("the user fills in the line chart title")
def user_fills_in_chart_title(context: Context) -> None:
    featured_chart_content = context.page.locator("#panel-child-promote-featured_chart-content")
    featured_chart_content.get_by_label("Title*").fill("Test Chart")


@step("the user fills in the chart audio description")
def user_fills_in_chart_audio_description(context: Context) -> None:
    featured_chart_content = context.page.locator("#panel-child-promote-featured_chart-content")
    featured_chart_content.get_by_label("Audio Description*").fill("This is the audio description")


@step("the user enters data into the chart table")
def user_enters_data_into_chart_table(context: Context) -> None:
    """Fill the table with test data by clicking and typing in each cell."""
    # Wait for the table editor to be ready
    context.page.wait_for_timeout(500)

    # Find the table editor
    table_editor = context.page.locator(".jexcel_container")
    expect(table_editor).to_be_visible()

    table_data = [["", "Series 1"], ["2005", "100"], ["2006", "101"]]

    # Fill each cell by clicking and typing
    for row_idx, row_data in enumerate(table_data):
        for col_idx, value in enumerate(row_data):
            table_editor.locator(f'td[data-x="{col_idx}"][data-y="{row_idx}"]').click()

            # Type the value
            context.page.keyboard.type(value)

            # Press Tab to move to next cell (or Enter for next row)
            if col_idx < len(row_data) - 1:
                context.page.keyboard.press("Tab")
            else:
                context.page.keyboard.press("Enter")


@given("a statistical article with valid streamfield content exists")
def a_statistical_article_with_valid_streamfield_content_exists(
    context: Context,
) -> None:
    """Create a statistical article page with a configured featured chart."""
    an_article_series_exists(context)
    content = [
        {
            "type": "section",
            "value": {
                "title": "The section heading",
                "content": [
                    {
                        "type": "rich_text",
                        "value": "The paragraph text",
                    }
                ],
            },
        }
    ]
    context.statistical_article_page = StatisticalArticlePageFactory(
        parent=context.article_series_page,
        title="Statistical article with featured chart",
        content=content,
    )
    context.statistical_article_page.save()


@given("a statistical article page with a configured featured chart exists")
def a_statistical_article_page_with_configured_featured_chart_exists(
    context: Context,
) -> None:
    """Create a statistical article page with a configured featured chart."""
    a_statistical_article_with_valid_streamfield_content_exists(context)
    featured_chart = [
        {
            "type": "line_chart",
            "value": {
                "title": "Test Chart",
                "subtitle": "Test Subtitle",
                "audio_description": "This is the audio description",
                "table": TableDataFactory(table_data=[["", "Series 1"], ["2005", "100"]]),
                "theme": "primary",
                "show_legend": True,
                "x_axis": {"title": ""},
                "y_axis": {"title": ""},
            },
        }
    ]
    context.statistical_article_page.featured_chart = featured_chart
    context.statistical_article_page.save()


@given("a statistical article page with a configured listing image exists")
def a_statistical_article_page_with_configured_listing_image_exists(
    context: Context,
) -> None:
    """Create a statistical article page with a configured listing image."""
    an_article_series_exists(context)
    content = [
        {
            "type": "section",
            "value": {
                "title": "The section heading",
                "content": [
                    {
                        "type": "rich_text",
                        "value": "The paragraph text",
                    }
                ],
            },
        }
    ]
    listing_image = ImageFactory(title="Test listing image")
    context.statistical_article_page = StatisticalArticlePageFactory(
        parent=context.article_series_page,
        title="Statistical article with listing image",
        listing_image=listing_image,
        content=content,
    )
    context.statistical_article_page.save()


@then("the page has a CSV download link for the chart")
def the_page_has_a_csv_download_link_for_the_chart(context: Context) -> None:
    """Check that the page has a CSV download link for the chart."""
    csv_download_link = context.page.get_by_role("link", name="Download CSV")
    expect(csv_download_link).to_be_visible()


@given("the statistical article page is not a featured article on its containing topic page")
def the_statistical_article_page_is_not_a_featured_article_on_its_containing_topic_page(
    context: Context,
) -> None:
    context.topic_page.featured_series = None
    context.topic_page.save_revision().publish()


@step("the user goes to edit the statistical article page")
def user_goes_to_edit_statistical_article_page(context: Context) -> None:
    """Navigate to edit the statistical article page."""
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.statistical_article_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the user leaves the featured chart fields blank")
def user_leaves_featured_chart_fields_blank(context: Context) -> None:
    featured_chart_content = context.page.locator("#panel-child-promote-featured_chart-content")
    expect(featured_chart_content.get_by_title("Insert a block")).to_be_visible()
    expect(featured_chart_content.locator("[data-streamfield-child]")).to_have_count(0)


@step('the user selects the "featured chart" preview mode')
def user_selects_featured_chart_preview_mode(context: Context) -> None:
    preview_button = context.page.locator('button[aria-label="Toggle preview"]')
    preview_button.click()
    context.page.wait_for_timeout(500)
    preview_mode_select = context.page.locator("#id_preview_mode")
    preview_mode_select.select_option(value="featured_article")
    context.page.wait_for_timeout(250)

    # Open preview in new tab for more reliable testing
    browser_context = context.playwright_context
    with browser_context.expect_page() as preview_page:
        context.page.get_by_role("link", name="Preview in new tab").click()
    context.preview_page = preview_page.value


@step("the user sees a preview of the containing Topic page")
def user_sees_a_preview_of_the_published_topic_page(context: Context) -> None:
    expect(context.preview_page.get_by_role("heading", name=context.topic_page.title)).to_be_visible()


@step("the topic page preview contains the featured article component")
def the_topic_page_preview_contains_the_featured_article_component(
    context: Context,
) -> None:
    context.featured_article_component = context.preview_page.locator("#featured")
    expect(
        context.featured_article_component.get_by_role("link", name=context.statistical_article_page.display_title)
    ).to_be_visible()


@given("the statistical article page is selected as the featured article on its containing topic page")
def the_statistical_article_page_is_selected_as_the_featured_article_on_its_containing_topic_page(
    context: Context,
) -> None:
    context.topic_page.featured_series = context.article_series_page
    context.topic_page.save_revision().publish()


@step("the user visits the containing topic page")
def user_visits_the_containing_topic_page(context: Context) -> None:
    context.page.goto(context.topic_page.full_url)


@step("the user sees the published topic page")
def user_sees_the_published_topic_page(context: Context) -> None:
    expect(context.page.get_by_role("heading", name=context.topic_page.title)).to_be_visible()


@step("the featured article is shown")
def the_featured_article_is_shown(context: Context) -> None:
    context.featured_article_component = context.page.locator("#featured")
    expect(
        context.featured_article_component.get_by_role("link", name=context.statistical_article_page.display_title)
    ).to_be_visible()


@step("the featured article component contains the featured chart")
def the_featured_article_component_contains_the_featured_chart(
    context: Context,
) -> None:
    expect(context.featured_article_component.get_by_text("Test Chart")).to_be_visible()


@step("the featured article component contains the featured article listing image")
def the_featured_article_component_contains_the_featured_article_listing_image(
    context: Context,
) -> None:
    expect(context.featured_article_component.locator("img")).to_be_visible()


@step("the user cannot delete the referenced headline figures")
def user_cannot_delete_the_referenced_headline_figures(context: Context) -> None:
    headline_figures_region = context.page.get_by_role("region", name="Headline figures")
    expect(headline_figures_region.get_by_role("button", name="Delete")).to_have_count(0)
