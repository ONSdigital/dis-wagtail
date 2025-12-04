from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@step("the user creates an information page as a child of the home page")
def user_creates_information_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Edit 'Home'").first.click()
    context.page.get_by_role("button", name="Actions", exact=True).click()
    context.page.get_by_role("link", name="Add a child page to 'Home'").click()
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
def user_returns_to_editing_the_statistical_article_page(context: Context) -> None:
    context.page.get_by_role("link", name="Test Info Page", exact=True).click()


def check_information_page_content(context: Context, default_language: bool = True) -> None:
    page = context.page
    expect(page.get_by_role("heading", name="Test Info Page")).to_be_visible()
    expect(page.get_by_text("My test information page")).to_be_visible()
    if default_language:
        expect(page.get_by_text("Last updated")).to_be_visible()
        expect(context.page.get_by_text("1 January 2024")).to_be_visible()
    else:
        expect(page.get_by_text("Diweddarwyd Diwethaf")).to_be_visible()
        expect(context.page.get_by_text("1 Ionawr 2024")).to_be_visible()

    expect(page.get_by_role("heading", name="Some example rich text content")).to_be_visible()
    expect(page.get_by_text("n∑i=0i2=(n2+n)(2n+1)")).to_be_visible()
    if default_language:
        expect(page.get_by_role("navigation", name="Related content").get_by_role("listitem")).to_be_visible()
    else:
        expect(page.get_by_role("navigation", name="Cynnwys cysylltiedig").get_by_role("listitem")).to_be_visible()

    expect(page.get_by_role("link", name="Test Home")).to_be_visible()
    expect(page.get_by_text("Our test home page")).to_be_visible()


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


@step('the date placeholder "{date_format}" is displayed in the "{textbox_text}" textbox')
def date_placeholder_is_displayed_in_date_input_field(context: Context, textbox_text: str, date_format: str) -> None:
    """Check date placeholder in the textbox."""
    expect(context.page.get_by_role("textbox", name=textbox_text)).to_have_attribute("placeholder", date_format)
