from behave import step, then, when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse
from playwright.sync_api import expect


@when("the user clicks publish page")
@when("publishes the page")
def user_clicks_publish_page(context: Context) -> None:
    context.page.get_by_role("button", name="More actions").click()
    context.page.get_by_role("button", name="Publish").click()


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


@when("the user refreshes the page")
def the_user_refreshes_the_page(context: Context):
    context.page.reload()


@step("the rich text toolbar is pinned")
def check_rich_text_toolbar_is_displayed_by_default(context: Context):
    expect(context.page.get_by_role("toolbar")).to_be_visible()


@when("the user unpins the rich text toolbar")
def the_user_unpins_the_rich_text_toolbar(context: Context):
    context.page.get_by_role("button", name="Unpin toolbar").click()


@then("the rich text toolbar is unpinned")
def check_rich_text_toolbar_is_unpinned(context: Context):
    expect(context.page.get_by_role("toolbar")).not_to_be_visible()


@step("the minimap is displayed")
def check_minimap_is_displayed(context: Context) -> None:
    expect(context.page.get_by_role("complementary", name="Minimap").locator("div").nth(1)).to_be_visible()


@when("the user hides the minimap")
def the_user_hides_the_minimap(context: Context):
    context.page.get_by_role("button", name="Toggle side panel").click()


@then("the minimap is hidden")
def the_minimap_is_hidden(context: Context):
    expect(context.page.get_by_role("complementary", name="Minimap").locator("div").nth(1)).not_to_be_visible()
