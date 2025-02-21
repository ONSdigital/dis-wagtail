from behave import then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect

from cms.themes.tests.factories import ThemePageFactory


@when("the user clicks publish page")
@when("publishes the page")
def user_clicks_publish_page(context: Context) -> None:
    publish_page(context)


@when('the user clicks "View Live" on the publish confirmation banner')
def user_clicks_view_live_on_publish_confirmation_banner(context: Context) -> None:
    context.page.get_by_role("link", name="View live").click()


@when('clicks the "{button_text}" button')
def clicks_the_given_button(context: Context, button_text: str):
    context.page.get_by_role("button", name=button_text).click()


@when("the user edits the {page} page")
def the_user_edits_the_topic_page(context: Context, page: str) -> None:
    the_page = page.lower().replace(" ", "_")
    if not the_page.endswith("_page"):
        the_page += "_page"
    edit_url = reverse("wagtailadmin_pages:edit", args=[getattr(context, the_page).pk])
    context.page.goto(f"{context.base_url}{edit_url}")


@when("the user tries to create a new theme page")
def user_tries_to_create_new_theme_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home", exact=True).click()
    context.page.get_by_role("link", name="Add child page").click()
    context.page.get_by_role("link", name="Theme page . A theme page,").click()


@when("the user tries to create a new topic page")
def user_tries_to_create_new_topic_page(context: Context) -> None:
    topic_theme = ThemePageFactory()
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home", exact=True).click()
    context.page.get_by_role("link", name=f"Add a child page to '{topic_theme.title}'").click()
    context.page.get_by_role("link", name="Topic page . A specific topic").click()


@when("the user tries to create a new information page")
def user_tries_to_create_new_information_page(context: Context) -> None:
    context.page.get_by_role("button", name="Pages").click()
    context.page.get_by_role("link", name="Home", exact=True).click()
    context.page.get_by_role("link", name="Add child page").click()
    context.page.get_by_role("link", name="Information page", exact=True).click()


@when("the user fills in the required topic page content")
@when("the user fills in the required theme page content")
def user_fills_required_topic_theme_page_content(context: Context):
    context.page_title = "Test Title"
    context.page.get_by_role("textbox", name="Title*").fill(context.page_title)
    context.page.get_by_role("region", name="Summary*").get_by_role("textbox").fill("Test Summary")


@then("the user can successfully publish the page")
def the_user_can_successfully_publish_the_page(context: Context):
    publish_page(context)
    expect(context.page.get_by_text(f"Page '{context.page_title}' created and published")).to_be_visible()


def publish_page(context: Context) -> None:
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()
