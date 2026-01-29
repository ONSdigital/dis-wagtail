# pylint: disable=not-callable
from behave import step, then, when
from behave.runner import Context
from django.conf import settings
from django.utils import translation
from playwright.sync_api import expect

from cms.core.custom_date_format import ons_date_format
from cms.standard_pages.models import InformationPage


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
    context.page.get_by_role("textbox", name="Title*").fill(context.page_title)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("My test information page")

    context.page.get_by_title("Insert a block").click()
    context.page.get_by_role("textbox", name="Section heading*").fill("Section 1")
    context.page.get_by_role("button", name="Insert a block").nth(1).click()
    context.page.get_by_text("Rich text").click()
    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill("Some example rich text content")

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


@when("the user updates the content of the information page")
def user_updates_info_page_contents(context: Context) -> None:
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Updated test information page")


@step("the user returns to editing the information page")
def user_returns_to_editing_the_statistical_article_page(context: Context) -> None:
    context.page.get_by_role("link", name="Test Info Page", exact=True).click()


def _get_information_page(context: Context) -> InformationPage | None:
    if hasattr(context, "page_id"):
        return InformationPage.objects.get(pk=context.page_id)
    return InformationPage.objects.filter(title=context.page_title).order_by("-last_published_at").first()


def check_information_page_content(context: Context, default_language: bool = True) -> None:
    page = context.page
    info_page = _get_information_page(context)

    if info_page is None:
        raise AssertionError("Information page not found for content checks.")

    language_code = settings.LANGUAGE_CODE if default_language else "cy"
    with translation.override(language_code):
        formatted_date = ons_date_format(info_page.last_published_at, "DATE_FORMAT")

    expect(page.get_by_role("heading", name="Test Info Page")).to_be_visible()
    expect(page.get_by_text("My test information page")).to_be_visible()

    if default_language:
        expect(page.get_by_text("Last updated")).to_be_visible()
        expect(page.locator("dl")).to_contain_text(f"Last updated: {formatted_date}")
    else:
        expect(page.get_by_text("Diweddarwyd Diwethaf")).to_be_visible()
        expect(page.locator("dl")).to_contain_text(f"Diweddarwyd Diwethaf: {formatted_date}")

    expect(page.locator("#section-1")).to_contain_text("Some example rich text content")
    expect(page.get_by_text("n∑i=0i2=(n2+n)(2n+1)")).to_be_visible()

    expect(page.get_by_role("link", name="Test Home")).to_be_visible()
    expect(page.get_by_text("Our test home page")).to_be_visible()

    expect(page.get_by_label("Sections in this page").get_by_role("heading")).to_contain_text("Contents")
    expect(page.get_by_role("link", name="Section 1")).to_be_visible()


@then("the new information page with the added content is displayed")
def check_new_information_is_displayed_with_content(context: Context) -> None:
    check_information_page_content(context)


@then("the published information page is displayed with English content")
def check_new_information_is_displayed_with_english_content(context: Context) -> None:
    check_information_page_content(context, default_language=True)


@then("the published information page is displayed with English content and Welsh livery")
def check_new_information_is_displayed_with_english_content_and_welsh_livery(
    context: Context,
) -> None:
    check_information_page_content(context, default_language=False)
