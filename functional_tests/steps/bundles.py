from behave import step, then  # pylint: disable=no-name-in-module
from behave.runner import Context
from playwright.sync_api import expect

from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.teams.models import Team


@step("a bundle has been created")
def a_bundle_has_been_created(context: Context) -> None:
    context.bundle = BundleFactory()


@step("is ready for review")
def the_bundle_is_ready_for_review(context: Context) -> None:
    context.bundle.status = BundleStatus.IN_REVIEW
    context.bundle.save(update_fields=["status"])


@step("has a preview team")
def a_bundle_has_a_preview_team(context: Context) -> None:
    context.team = Team.objects.create(identifier="preview-team", name="Preview team")
    BundleTeam.objects.create(parent=context.bundle, team=context.team)


@step("the viewer is in the preview team")
def the_viewer_is_in_the_preview_team(context: Context) -> None:
    user = context.user_data["user"]
    user.teams.add(context.team)


@step("the user goes to the bundle creation page")
def the_user_goes_to_the_bundle_creation_page(context: Context) -> None:
    context.page.goto(context.base_url + "/admin/bundle/new/")


@step("the user opens the release calendar page chooser")
def the_user_selects_a_release_calendar(context: Context) -> None:
    context.page.get_by_role("button", name="Choose Release Calendar page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open


@step("the user opens the page chooser")
def the_user_opens_page_chooser(context: Context) -> None:
    context.page.get_by_role("button", name="Add page").click()
    context.page.wait_for_timeout(100)
    context.page.get_by_role("button", name="Choose a page").click()
    context.page.wait_for_timeout(250)  # Wait for the modal to open


@step("the locale column is displayed in the chooser")
def the_locale_column_is_displayed(context: Context) -> None:
    modal = context.page.locator(".modal-body")
    modal.get_by_role("columnheader", name="Locale").is_visible()


@then("the date placeholder is displayed in the date field for bundles")
def datetime_placeholder_bundles(context: Context):
    expect(context.page.get_by_role("textbox", name="Publication date")).to_have_attribute(
        "placeholder", "YYYY-MM-DD HH:MM"
    )
