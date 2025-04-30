from behave import step  # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.teams.models import Team
from functional_tests.step_helpers.users import create_user


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


@step("the user can add Bundles created by user")
def a_bundle_with_name_item_name_has_been_created_by_username(context: Context) -> None:
    context.bundle = BundleFactory(created_by=context.user_data["user"])


@step("Bundle has the creator removed")
def created_by_has_been_deleted(context: Context) -> None:
    context.bundle.created_by = None
    context.bundle.save(update_fields=["created_by"])


@step('a "{user_type}" logs into the admin site with username "{username}"')
def user_logs_in_with_username(context: Context, user_type: str, username: str) -> None:
    context.user_data = create_user(user_type)
    context.page.goto(f"{context.base_url}/admin/login/")
    context.page.get_by_placeholder("Enter your username").fill(context.user_data[username])
    context.page.get_by_placeholder("Enter password").fill(context.user_data["password"])
    context.page.get_by_role("button", name="Sign in").click()


@step("the user can inspect Bundle details")
def the_user_can_see_the_bundle_details(context: Context) -> None:
    context.page.get_by_role("link", name="Bundles", exact=True).click()
    context.page.get_by_role("button", name=f"More options for '{context.bundle.name}'").click()
    context.page.get_by_role("link", name=f"Inspect '{context.bundle.name}'").click()
