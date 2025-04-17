from behave import given, step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.articles.tests.factories import ArticleSeriesPageFactory
from cms.topics.tests.factories import TopicPageFactory


@given("an article series page exists")
def the_topic_page_has_a_statistical_article_in_a_series(context: Context):
    context.topic_page = TopicPageFactory(title="Test Topic")
    context.article_series = ArticleSeriesPageFactory(title="PSF", parent=context.topic_page)


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
    page.locator(".ons-corrections-notices__banner").click()
    page.get_by_role("link", name="View superseded version").click()


@step("the user adds a table with pasted content")
def user_adds_table_with_pasted_content(context: Context):
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


@then("the user can view the superseded statistical article page")
def user_can_view_the_superseded_statistical_article_page(context: Context):
    expect(context.page.get_by_role("heading", name="The article page")).to_be_visible()
    expect(context.page.get_by_text("Content", exact=True)).to_be_visible()


@step("the user returns to editing the statistical article page")
def user_returns_to_editing_the_statistical_article_page(context: Context):
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.article_series.get_latest().id,))
    context.page.goto(f"{context.base_url}{edit_url}")


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


@step("the user adds headline figures")
def user_adds_headline_figures(context: Context):
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Insert a block").click()
    page.wait_for_timeout(100)
    panel.get_by_role("button", name="Add", exact=True).nth(0).click()
    page.wait_for_timeout(100)
    panel.get_by_label("Title*").nth(0).fill("First headline figure")
    panel.get_by_label("Figure*").nth(0).fill("~123%")
    panel.get_by_label("Supporting text*").nth(0).fill("First supporting text")
    panel.get_by_label("Title*").nth(1).fill("Second headline figure")
    panel.get_by_label("Figure*").nth(1).fill("~321%")
    panel.get_by_label("Supporting text*").nth(1).fill("Second supporting text")


@step("the user edits the ancestor topic")
def user_edits_the_ancestor_topic(context: Context):
    edit_url = reverse("wagtailadmin_pages:edit", args=(context.topic_page.id,))
    context.page.goto(f"{context.base_url}{edit_url}")


@step("the user views the topic page")
def user_views_the_topic_page(context: Context):
    context.page.goto(f"{context.base_url}{context.topic_page.url}")


@step("the user clicks to add headline figures to the topic page")
def user_clicks_to_add_headline_figures_to_the_topic_page(context: Context, *, button_index: int = 0):
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Insert a block").nth(button_index).click()
    page.wait_for_timeout(100)
    panel.get_by_role("button", name="Choose Article Series page").click()
    page.wait_for_timeout(100)  # Wait for modal to open


@step("the user adds two headline figures to the topic page")
def user_adds_two_headline_figures_to_the_topic_page(context: Context):
    page = context.page
    user_clicks_to_add_headline_figures_to_the_topic_page(context)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(0).click()
    user_clicks_to_add_headline_figures_to_the_topic_page(context, button_index=1)
    page.locator(".modal-content").get_by_role("link", name="PSF").nth(1).click()


@step("the user reorders the headline figures on the topic page")
def user_reorders_the_headline_figures_on_the_topic_page(context: Context):
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Move up").nth(1).click()


@step("the user reorders the headline figures on the Statistical Article Page")
def user_reorders_the_headline_figures_on_the_statistical_article_page(context: Context):
    page = context.page
    panel = page.locator("#panel-child-content-headline_figures-content")
    panel.get_by_role("button", name="Move up").nth(2).click()


@step("the user adds another correction using the add button at the bottom")
def user_adds_a_correction_using_bottom_add_button(context: Context):
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
def user_adds_a_notice(context: Context):
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


@then("the published statistical article page has the added correction")
def the_published_statistical_article_page_has_the_added_correction(context: Context):
    expect(context.page.get_by_role("heading", name="Corrections")).to_be_visible()
    expect(context.page.get_by_text("13 March 2025 1:59p.m.")).to_be_hidden()
    expect(context.page.get_by_text("Correction text")).to_be_hidden()


@then("the user can expand and collapse {block_type} details")
def user_can_click_on_view_detail_to_expand_block(context: Context, block_type: str):
    if block_type == "correction":
        text = "Correction text"
        date = "13 March 2025 1:59p.m."
    else:
        text = "Notice text"
        date = "15 March 2025 1:59p.m."

    context.page.get_by_text("Show detail").click()
    expect(context.page.get_by_text(text)).to_be_visible()
    expect(context.page.get_by_text(date)).to_be_visible()
    if block_type == "correction":
        expect(context.page.get_by_role("link", name="View superseded version")).to_be_visible()

    context.page.wait_for_timeout(500)
    context.page.get_by_text("Close detail").click()
    context.page.wait_for_timeout(500)
    expect(context.page.get_by_text(text)).to_be_hidden()
    expect(context.page.get_by_text(date)).to_be_hidden()


@then("the published statistical article page has the corrections and notices block")
def the_published_statistical_article_page_has_the_corrections_and_notices_block(context: Context):
    expect(context.page.get_by_role("heading", name="Corrections and notices")).to_be_visible()


@then("the published statistical article page has the added headline figures")
@then("the published topic page has the added headline figures")
@then("the headline figures are shown")
def the_published_statistical_article_page_has_the_added_headline_figures(context: Context):
    page = context.page
    expect(page.get_by_text("First headline figure")).to_be_visible()
    expect(page.get_by_text("~123%")).to_be_visible()
    expect(page.get_by_text("Second headline figure")).to_be_visible()
    expect(page.get_by_text("~321%")).to_be_visible()
    expect(page.get_by_text("First supporting text")).to_be_visible()
    expect(page.get_by_text("Second supporting text")).to_be_visible()


@then("the published topic page has the added headline figures in the correct order")
def the_published_topic_page_has_the_added_headline_figures_in_the_correct_order(context: Context):
    page = context.page
    headline_block = page.locator(".headline-figures .headline-figures__block")
    expect(headline_block.nth(0).get_by_text("First headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("Second headline figure")).to_be_visible()


@then("the published topic page has reordered headline figures")
def the_published_topic_page_has_reordered_headline_figures(context: Context):
    page = context.page
    headline_block = page.locator(".headline-figures .headline-figures__block")
    expect(headline_block.nth(0).get_by_text("Second headline figure")).to_be_visible()
    expect(headline_block.nth(1).get_by_text("First headline figure")).to_be_visible()


@then("the headline figures on the topic page link to the statistical page")
def the_headline_figures_on_the_topic_page_link_to_the_statistical_page(context: Context):
    page = context.page
    page.get_by_text("First headline figure").click()
    expect(page.get_by_role("heading", name="The article page")).to_be_visible()
    page.go_back()
    page.get_by_text("Second headline figure").click()
    expect(page.get_by_role("heading", name="The article page")).to_be_visible()


@then('the user can click on "Show detail" to expand the corrections and notices block')
def user_can_click_on_show_detail_to_expand_corrections_and_notices_block(context: Context):
    context.page.get_by_text("Show detail").click()
    expect(context.page.get_by_text("Notice text")).to_be_visible()
    expect(context.page.get_by_text("15 March 2025 1:59p.m.")).to_be_visible()

    expect(context.page.get_by_text("Correction text")).to_be_visible()
    expect(context.page.get_by_text("13 March 2025 1:59p.m.")).to_be_visible()
    expect(context.page.get_by_role("link", name="View superseded version")).to_be_visible()


@then('the user can click on "Close detail" to collapse the corrections and notices block')
def user_can_click_on_hide_detail_to_collapse_corrections_and_notices_block(context: Context):
    context.page.get_by_text("Close detail").click()

    expect(context.page.get_by_text("Notice text")).to_be_hidden()
    expect(context.page.get_by_text("15 March 2025 1:59p.m.")).to_be_hidden()

    expect(context.page.get_by_text("Correction text")).to_be_hidden()
    expect(context.page.get_by_text("13 March 2025 1:59p.m.")).to_be_hidden()


@then("the published statistical article page has corrections in chronological order")
def the_published_statistical_article_page_has_corrections_in_chronological_order(context: Context):
    expect(context.page.locator("#corrections div:first-child").get_by_text("14 March 2025 1:59p.m.")).to_be_hidden()
    expect(context.page.locator("#corrections div:nth-child(2)").get_by_text("13 March 2025 1:59p.m.")).to_be_hidden()


@then("the published statistical article page has the added notice")
def the_published_statistical_article_page_has_the_added_notice(context: Context):
    expect(context.page.get_by_role("heading", name="Notices")).to_be_visible()
    expect(context.page.get_by_text("15 March 2025 1:59p.m.")).to_be_hidden()
    expect(context.page.get_by_text("Notice text")).to_be_hidden()


@then("the user can edit the correction")
def user_cannot_edit_the_correction(context: Context):
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    page.locator("#tab-label-corrections_and_notices").click()
    expect(page.locator("#corrections-0-value-when")).to_be_editable()
    page.wait_for_timeout(50)  # added to prevent flakiness, as the test following this check would sometimes fail


@then("the user cannot delete the correction")
def user_cannot_delete_the_correction(context: Context):
    page = context.page
    page.wait_for_timeout(500)  # added to allow JS to be ready
    page.locator("#tab-label-corrections_and_notices").click()
    expect(
        page.locator("#panel-child-corrections_and_notices-corrections-content [data-streamfield-action='DELETE']")
    ).to_be_hidden()
