# pylint: disable=not-callable
from behave import step, then, when
from behave.runner import Context
from django.conf import settings
from playwright.sync_api import expect
from wagtail.models import Locale

from cms.home.models import HomePage
from cms.standard_pages.tests.factories import InformationPageFactory


@step("an information page exists")
def an_information_page_exists(context: Context) -> None:
    context.information_page = InformationPageFactory()


@step("a published information page exists")
def a_published_information_page_exists(context: Context) -> None:
    home_page = HomePage.objects.get(locale__language_code=settings.LANGUAGE_CODE)
    context.information_page = InformationPageFactory(
        title="Test Info Page",
        summary="<p>My test information page</p>",
        last_updated="2024-01-01",
        content=[
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
            {
                "type": "equation",
                "value": {
                    "equation": "$$\\sum_{i=0}^n i^2 = \\frac{(n^2+n)(2n+1)}{6}$$",
                },
            },
        ],
    )

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
        {
            "type": "equation",
            "value": {
                "equation": "$$\\sum_{i=0}^n i^2 = \\frac{(n^2+n)(2n+1)}{6}$$",
            },
        },
    ]

    context.welsh_information_page.save_revision().publish()


@step("the user creates an information page as a child of the home page")
def user_creates_information_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Edit 'Home'").first.click()
    context.page.get_by_role("button", name="Actions", exact=True).click()
    context.page.get_by_role("link", name="Add child page").click()
    context.page.get_by_role("link", name="Information page", exact=True).click()


@step("the user adds content to the new information page")
def user_adds_info_page_contents(context: Context) -> None:
    context.page_title = "Test Info Page"
    context.page.get_by_placeholder("Page title*").fill(context.page_title)

    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My test information page")

    context.page.get_by_role("textbox", name="Last updated").fill("2024-01-01")
    context.page.get_by_role("textbox", name="Last updated").press("Enter")

    context.page.get_by_role("button", name="Insert a block").click()
    context.page.get_by_role("option", name="Rich text").locator("div").first.click()
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Some example rich text content")
    context.page.get_by_role("region", name="Rich text *").get_by_label("Insert a block").click()
    context.page.get_by_text("Heading 3").click()

    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.get_by_text("Equation").click()
    context.page.locator('[data-controller="wagtailmathjax"]').fill("$$\\sum_{i=0}^n i^2 = \\frac{(n^2+n)(2n+1)}{6}$$")
    context.page.wait_for_timeout(5000)

    context.page.get_by_role("button", name="Insert a block").nth(2).click()
    context.page.get_by_text("Related links").click()
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("cell", name="Home English", exact=True).get_by_role("link").click()
    context.page.get_by_role("textbox", name="Title", exact=True).fill("Test Home")
    context.page.get_by_role("textbox", name="Description").fill("Our test home page")

    context.page.get_by_role("button", name="Add related pages").click()
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.get_by_role("cell", name="Home English", exact=True).get_by_role("link").click()


@when("the user updates the content of the information page")
def user_updates_info_page_contents(context: Context) -> None:
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Updated test information page")


@step("the user returns to editing the information page")
def user_returns_to_editing_the_information_page(context: Context) -> None:
    context.page.get_by_role("link", name="Test Info Page", exact=True).click()


def check_information_page_content(context: Context, default_language: bool = True, extended: bool = True) -> None:
    page = context.page
    expect(page.get_by_role("heading", name="Test Info Page")).to_be_visible()
    expect(page.get_by_text("My test information page")).to_be_visible()
    if default_language:
        expect(page.get_by_text("Last updated")).to_be_visible()
        expect(context.page.get_by_text("1 January 2024")).to_be_visible()
    else:
        expect(page.get_by_text("Diweddarwyd Diwethaf")).to_be_visible()
        expect(context.page.get_by_text("1 Ionawr 2024")).to_be_visible()

    expect(page.get_by_text("Some example rich text content")).to_be_visible()
    if default_language:
        expect(page.get_by_role("heading", name="Related links")).to_be_visible()
        expect(page.get_by_text("Our test home page")).to_be_visible()
    else:
        expect(page.get_by_role("heading", name="Dolenni cysylltiedig")).to_be_visible()
        expect(page.get_by_text("Ein tudalen gartref prawf")).to_be_visible()

    expect(page.get_by_role("link", name="Test Home")).to_be_visible()
    expect(page.get_by_text("Our test home page")).to_be_visible()

    if extended:
        expect(page.get_by_text("n∑i=0i2=(n2+n)(2n+1)")).to_be_visible()


@then("the new information page with the added content is displayed")
def check_new_information_is_displayed_with_content(context: Context) -> None:
    check_information_page_content(context)


@then("the published information page is displayed with English content")
def check_new_information_is_displayed_with_english_content(context: Context) -> None:
    check_information_page_content(context, default_language=True)


@then("the published information page is displayed with basic English content")
def check_new_information_is_displayed_with_basic_english_content(context: Context) -> None:
    check_information_page_content(context, default_language=True, extended=False)


@then("the published information page is displayed with English content and Welsh livery")
def check_new_information_is_displayed_with_english_content_and_welsh_livery(
    context: Context,
) -> None:
    check_information_page_content(context, default_language=False)


@then("the information page preview contains the populated data")
def the_information_page_preview_contains_the_data(context: Context) -> None:
    iframe = context.page.frame_locator("#w-preview-iframe")
    check_information_page_content(iframe)


@step('the date placeholder "{date_format}" is displayed in the "{textbox_text}" textbox')
def date_placeholder_is_displayed_in_date_input_field(context: Context, textbox_text: str, date_format: str) -> None:
    """Check date placeholder in the textbox."""
    expect(context.page.get_by_role("textbox", name=textbox_text)).to_have_attribute("placeholder", date_format)
