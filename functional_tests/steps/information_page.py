# pylint: disable=not-callable
from typing import TYPE_CHECKING

from behave import step, then, when
from behave.runner import Context
from django.conf import settings
from django.urls import reverse
from django.utils import translation
from playwright.sync_api import expect
from wagtail.models import Locale

from cms.core.custom_date_format import ons_date_format
from cms.home.models import HomePage
from cms.standard_pages.models import InformationPage
from cms.standard_pages.tests.factories import IndexPageFactory, InformationPageFactory
from functional_tests.step_helpers.utils import get_page_from_context, str_to_bool

if TYPE_CHECKING:
    from playwright.sync_api import FrameLocator
    from playwright.sync_api import Page as PlaywrightPage


def create_information_page(context: Context) -> None:
    home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
    content = [
        {"type": "rich_text", "value": "<p>Some example rich text content</p>"},
        {
            "type": "related_links",
            "value": [
                {"page": home_page.pk, "title": "Test Home", "description": "Our test home page"},
                {
                    "page": home_page.pk,
                },
            ],
        },
    ]

    kwargs = {
        "title": "Test Info Page",
        "summary": "<p>My test information page</p>",
        "content": [{"type": "section", "value": {"content": content, "title": "Section 1"}}],
    }
    if index_page := get_page_from_context(context, "index"):
        kwargs["parent"] = index_page

    context.information_page = InformationPageFactory(**kwargs)


@step("a index page exists")
def an_index_page_exists(context: Context) -> None:
    context.index_page = IndexPageFactory()


@step("a published index page exists")
def a_published_index_page_exists(context: Context) -> None:
    context.index_page = IndexPageFactory()
    context.index_page.save_revision().publish()


@step("an information page exists")
def an_information_page_exists(context: Context) -> None:
    create_information_page(context)


@step("a published information page exists")
def a_published_information_page_exists(context: Context) -> None:
    create_information_page(context)
    context.information_page.save_revision().publish()

    cy = Locale.objects.get(language_code="cy")
    if not context.information_page.has_translation(cy):
        context.welsh_information_page = context.information_page.copy_for_translation(
            locale=cy, copy_parents=True, alias=True
        )
    else:
        context.welsh_information_page = context.information_page.get_translation(cy)


@step("a published information page translation exists")
def a_published_information_page_translation_exists(context: Context) -> None:
    if not hasattr(context, "welsh_information_page"):
        a_published_information_page_exists(context)

    home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)

    context.welsh_information_page.alias_of = None
    context.welsh_information_page.title = "Tudalen Gwybodaeth Profi"
    context.welsh_information_page.summary = "<p>Tudalen wybodaeth fy mhrawf<p>"
    context.welsh_information_page.content = [
        {
            "type": "section",
            "value": {
                "title": "Section 1",
                "content": [
                    {"type": "rich_text", "value": "<p>Rhywfaint o gynnwys testun enghreifftiol</p>"},
                    {
                        "type": "related_links",
                        "value": [
                            {"page": home_page.pk, "title": "Test Home", "description": "Ein tudalen gartref prawf"},
                            {
                                "page": home_page.pk,
                            },
                        ],
                    },
                ],
            },
        }
    ]

    context.welsh_information_page.save_revision().publish()


def _get_information_page(context: Context) -> InformationPage:
    """Retrieve the information page from context.

    Expects either context.information_page to be set directly,
    or context.page_title to perform a lookup (and cache the result).
    """
    if info_page := get_page_from_context(context, "information"):
        return info_page

    if hasattr(context, "page_title"):
        info_page = InformationPage.objects.filter(title=context.page_title).order_by("-last_published_at").first()
        if info_page:
            context.information_page = info_page  # Cache for subsequent calls
            return info_page

    raise AssertionError(
        "Information page not found. Ensure context.information_page is set "
        "or context.page_title matches an existing page."
    )


def _assert_information_pages_in_order(context: Context, expected_titles: list[str], label: str) -> None:
    list_items = context.page.locator(".ons-document-list").first.locator(".ons-document-list__item").all()
    actual_titles = []

    for item in list_items:
        title_link = item.locator(".ons-document-list__item-title a").first
        title = title_link.text_content().strip()
        actual_titles.append(title)

    assert actual_titles == expected_titles, (
        f"Expected {label} information pages in order {expected_titles}, but got {actual_titles}"
    )


@step("the user goes to add an information page as a child of the index page")
def user_creates_information_page(context: Context) -> None:
    if not hasattr(context, "index_page"):
        an_index_page_exists(context)

    add_url = reverse(
        "wagtailadmin_pages:add",
        args=("standard_pages", "informationpage", context.index_page.pk),
    )
    context.page.goto(f"{context.base_url}{add_url}")


@step("the user adds content to the new information page")
def user_adds_info_page_contents(context: Context) -> None:
    context.page_title = "Test Info Page"
    context.page.get_by_role("textbox", name="Title*").fill(context.page_title)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My test information page")

    context.page.get_by_title("Insert a block").click()
    context.page.get_by_role("textbox", name="Section heading*").fill("Section 1")
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.get_by_text("Rich text").click()
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Some example rich text content")

    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.get_by_text("Related links").click()
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("cell", name="Home English", exact=True).get_by_role("link").click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Test Home")
    context.page.get_by_role("textbox", name="Description").fill("Our test home page")


@step("the user adds an equation")
def user_adds_equation(context: Context) -> None:
    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.get_by_text("Equation", exact=True).click()
    context.page.locator('[data-controller="wagtailmathjax"]').fill("$$\\sum_{i=0}^n i^2 = \\frac{(n^2+n)(2n+1)}{6}$$")
    context.page.wait_for_timeout(5000)


@when("the user updates the content of the information page")
def user_updates_info_page_contents(context: Context) -> None:
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Updated test information page")


@step("the user returns to editing the information page")
def user_returns_to_editing_the_information_page(context: Context) -> None:
    context.page.get_by_role("link", name="Test Info Page", exact=True).click()


def check_information_page_content(
    page_or_frame: PlaywrightPage | FrameLocator,
    information_page: InformationPage | None = None,
    default_language: bool = True,
) -> None:
    expect(page_or_frame.get_by_role("heading", name="Test Info Page")).to_be_visible()
    expect(page_or_frame.get_by_text("My test information page")).to_be_visible()
    expect(page_or_frame.locator("#section-1")).to_contain_text("Some example rich text content")

    if information_page is not None:
        language_code = settings.LANGUAGE_CODE if default_language else "cy"
        with translation.override(language_code):
            formatted_date = ons_date_format(information_page.last_published_at, "DATE_FORMAT")

        if default_language:
            expect(page_or_frame.locator("dl")).to_contain_text(f"Last updated: {formatted_date}")
        else:
            expect(page_or_frame.locator("dl")).to_contain_text(f"Diweddarwyd Diwethaf: {formatted_date}")

    if default_language:
        expect(page_or_frame.get_by_text("Our test home page")).to_be_visible()
        expect(page_or_frame.get_by_label("Sections in this page").get_by_role("heading")).to_contain_text("Contents")
        expect(page_or_frame.get_by_label("Sections in this page")).to_contain_text("Section 1")
    else:
        expect(page_or_frame.get_by_label("Adrannau ar y dudalen hon").get_by_role("heading")).to_contain_text(
            "Cynnwys"
        )
        expect(page_or_frame.get_by_label("Adrannau ar y dudalen hon")).to_contain_text("Section 1")

    expect(page_or_frame.get_by_role("link", name="Test Home")).to_be_visible()
    expect(page_or_frame.get_by_text("Our test home page")).to_be_visible()


@then("the new information page with the added content is displayed")
def check_new_information_is_displayed_with_content(context: Context) -> None:
    check_information_page_content(context.page)


@then("the published information page is displayed with English content")
def check_new_information_is_displayed_with_english_content(context: Context) -> None:
    check_information_page_content(context.page, information_page=context.information_page, default_language=True)


@then("the published information page is displayed with basic English content")
def check_new_information_is_displayed_with_basic_english_content(context: Context) -> None:
    check_information_page_content(context.page, information_page=context.information_page, default_language=True)


@then("the published information page is displayed with English content and Welsh livery")
def check_new_information_is_displayed_with_english_content_and_welsh_livery(
    context: Context,
) -> None:
    check_information_page_content(context.page, default_language=False)


@then("the information page preview contains the populated data")
def the_information_page_preview_contains_the_data(context: Context) -> None:
    iframe = context.page.frame_locator("#w-preview-iframe")
    check_information_page_content(iframe)


@step('the date placeholder "{date_format}" is displayed in the "{textbox_text}" textbox')
def date_placeholder_is_displayed_in_date_input_field(context: Context, textbox_text: str, date_format: str) -> None:
    """Check date placeholder in the textbox."""
    expect(context.page.get_by_role("textbox", name=textbox_text)).to_have_attribute("placeholder", date_format)


@step('the user adds the taxonomy topic "{topic_name}" twice')
def user_adds_taxonomy_topic_twice(context: Context, topic_name: str) -> None:
    page = context.page
    page.get_by_role("tab", name="Taxonomy").click()

    for _ in range(2):
        page.get_by_role("button", name="Add topics").click()
        page.get_by_role("checkbox", name=topic_name).check()
        page.get_by_role("button", name="Confirm selection").click()


@then("the duplicate topic error message is shown")
def only_one_instance_of_topic_is_saved(context: Context) -> None:
    page = context.page
    page.get_by_role("tab", name="Taxonomy").click()
    expect(page.locator("#panel-child-taxonomy-topics-content")).to_contain_text(
        "Please correct the duplicate data for page and topic, which must be unique."
    )


@step("the index page has the following information pages:")
def index_page_has_information_pages(context: Context) -> None:
    if not hasattr(context, "index_page"):
        context.index_page = IndexPageFactory(title="Index Page")

    context.index_information_pages = []

    for row in context.table:
        page_name = row.get("page_name")
        live_value = row.get("live", "true")

        if not page_name:
            raise ValueError("Information pages table must include a 'page_name' column")

        live = str_to_bool(live_value)

        info_page = InformationPageFactory(parent=context.index_page, title=page_name, live=live)

        context.index_information_pages.append(info_page)


@when("the user visits the live index page")
def user_visits_index_page(context: Context) -> None:
    context.page.goto(f"{context.base_url}{context.index_page.url}")


@when("the user visits the index page preview")
def user_visits_index_page_preview(context: Context) -> None:
    edit_url = reverse("wagtailadmin_pages:edit", args=[context.index_page.pk])

    context.page.goto(f"{context.base_url}{edit_url}")

    preview_button = context.page.locator('button[aria-label="Toggle preview"]')
    preview_button.click()

    context.page.wait_for_timeout(500)

    with context.page.expect_popup() as preview_tab:
        context.page.get_by_role("link", name="Preview in new tab").click()
    # closes context.page (admin page)
    context.page.close()
    # assigns context.page to the pop up tab
    context.page = preview_tab.value


@then("the live index page lists only live information pages in alphabetical order")
def live_index_page_lists_only_live_information_pages(context: Context) -> None:
    expected_titles = sorted(
        [page.title for page in context.index_information_pages if page.live],
        key=str.casefold,
    )

    _assert_information_pages_in_order(context, expected_titles, "live")


@then("the index page preview lists live and draft information pages in alphabetical order")
def preview_index_page_lists_live_and_draft_information_pages(context: Context) -> None:
    expected_titles = sorted(
        [page.title for page in context.index_information_pages],
        key=str.casefold,
    )

    _assert_information_pages_in_order(context, expected_titles, "preview")


@then("the equation is rendered")
def the_equation_is_rendered(context: Context) -> None:
    expect(context.page.get_by_text("n∑i=0i2=(n2+n)(2n+1)")).to_be_visible()
