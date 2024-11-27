from behave import given  # pylint: disable=E0611
from behave.runner import Context


@given("a contact details snippet exists")
def create_contact_details_snippet(context: Context):
    """Create a contact details snippet."""
    # TODO this import fails at the top level with error:  pylint: disable=W0511
    #  "django.core.exceptions.AppRegistryNotReady: Models aren't loaded yet."
    #   Find a better solution
    from functional_tests.factories import ContactDetailsFactory  # pylint: disable=C0415

    context.contact_details_snippet = ContactDetailsFactory()
