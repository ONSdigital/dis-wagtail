from behave import given, step, then  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect


@given("a CMS user creates the Welsh locale")
def user_goes_to_add_new_article_page(context: Context) -> None:
    context.page.goto(f"{context.base_url}/admin/locales/new/")
    context.page.get_by_role("button", name="Create").click()


@given("a CMS user edits the home page")
def user_goes_to_edit_home_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Edit 'Home'").click()


@given("the user creates a Welsh version of the home page")
def user_creates_welsh_version_of_home_page(context: Context) -> None:
    user_goes_to_edit_home_page(context)
    user_creates_welsh_version_of_page(context)
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Edit 'Home'").nth(1).click()
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


@then("the user can see the option to add a translation")
def user_can_see_the_option_to_add_a_translation(context) -> None:
    context.page.get_by_role("button", name="Actions", exact=True).click()
    expect(context.page.get_by_role("link", name="Translate")).to_be_visible()


@step("the user creates a Welsh version of the page")
def user_creates_welsh_version_of_page(context: Context) -> None:
    context.page.locator("#w-slim-header-buttons").get_by_role("button", name="Actions", exact=True).click()
    context.page.get_by_role("link", name="Translate").click()
    context.page.locator("#id_locales_0").check()
    context.page.get_by_role("button", name="Submit").click()


@step("the user switches to the Welsh locale")
def user_switches_to_welsh_locale(context: Context) -> None:
    context.page.get_by_role("button", name="Status").click()
    context.page.get_by_role("button", name="Switch locales").click()
    context.page.get_by_role("link", name="Welsh").click()


@step("the user converts the alias into an ordinary page")
def user_converts_the_alias_into_an_ordinary_page(context: Context) -> None:
    context.page.get_by_role("link", name="Convert this alias into an ordinary page").click()
    context.page.get_by_role("button", name="Yes, convert it").click()


@step("the user adds Welsh content to the information page")
def user_populates_the_information_page_with_welsh_content(context: Context) -> None:
    context.page.get_by_placeholder("Page title*").fill("Tudalen Gwybodaeth Profi")

    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Tudalen wybodaeth fy mhrawf")

    context.page.get_by_role("region", name="Rich text *").get_by_role("textbox").fill(
        "Rhywfaint o gynnwys testun enghreifftiol"
    )


@step("the user switches the page language to English")
def user_switches_page_language_to_english(context: Context) -> None:
    context.page.locator(".ons-header__top").get_by_role("link", name="English").click()


@step("the user switches the page language to Welsh")
def user_switches_page_language_to_welsh(context: Context) -> None:
    context.page.locator(".ons-header__top").get_by_role("link", name="Cymraeg").click()


@then("the published information page is displayed with Welsh content")
def check_new_information_is_displayed_with_welsh_content(context: Context) -> None:
    expect(context.page.get_by_role("heading", name="Tudalen Gwybodaeth Profi")).to_be_visible()
    expect(context.page.get_by_text("Tudalen wybodaeth fy mhrawf")).to_be_visible()
    expect(context.page.get_by_role("heading", name="Rhywfaint o gynnwys testun enghreifftiol")).to_be_visible()


@then("the page furniture is displayed in English")
def check_page_furniture_is_displayed_in_english(context: Context) -> None:
    expect(context.page.get_by_text("Mae'r holl gynnwys ar gael o dan delerau'r")).to_be_visible()


@then("the page furniture is displayed in Welsh")
def check_page_furniture_is_displayed_in_welsh(context: Context) -> None:
    expect(context.page.get_by_text("Mae'r holl gynnwys ar gael o dan delerau'r")).to_be_visible()


@then("a message is displayed explaining that the content is not translated")
def check_message_is_displayed(context: Context) -> None:
    expect(
        context.page.get_by_text(
            "This page is currently not available in your locale. The English version is shown instead."
        )
    ).to_be_visible()
