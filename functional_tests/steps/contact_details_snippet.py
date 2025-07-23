from behave import given  # pylint: disable=no-name-in-module
from behave.runner import Context

from cms.core.tests.factories import ContactDetailsFactory


@given("a contact details snippet exists")
def create_contact_details_snippet(context: Context):
    context.contact_details_snippet = ContactDetailsFactory()
