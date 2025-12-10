# pylint: disable=not-callable
from behave import given
from behave.runner import Context

from cms.core.tests.factories import ContactDetailsFactory


@given("a contact details snippet exists")
def create_contact_details_snippet(context: Context) -> None:
    context.contact_details_snippet = ContactDetailsFactory()
