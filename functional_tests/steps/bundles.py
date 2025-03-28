from behave import step  # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.bundles.tests.factories import BundleFactory


@step("a bundle has been created")
def a_bundle_has_been_created(context: Context) -> None:
    context.bundle = BundleFactory()
