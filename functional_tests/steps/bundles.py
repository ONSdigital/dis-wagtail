from behave import step  # pylint: disable=no-name-in-module

from behave.runner import Context

from cms.bundles.enums import BundleStatus
from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory
from cms.teams.models import Team
from cms.users.models import User


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


@step('a bundle has been created by "{user}"')
def a_bundle_with_name_item_name_has_been_created_by_username(context: Context, user: User) -> None:
    context.bundle = BundleFactory(created_by=user)


@step('Bundle has the creator removed')
def created_by_has_been_deleted(context: Context) -> None:
    context.bundle.created_by = None
    context.bundle.save(update_fields=["created_by"])
