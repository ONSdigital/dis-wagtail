from behave import when  # pylint: disable=no-name-in-module
from behave.runner import Context
from django.urls import reverse


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
