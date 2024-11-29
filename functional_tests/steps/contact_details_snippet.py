from behave import given  # pylint: disable=E0611
from behave.runner import Context

from functional_tests.step_helpers.factories import ContactDetailsFactory


@given("a contact details snippet exists")
def create_contact_details_snippet(context: Context):
    """Create a contact details snippet."""
    context.contact_details_snippet = ContactDetailsFactory()
