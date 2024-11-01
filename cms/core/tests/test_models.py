import pytest

from cms.core.models import ContactDetails

pytestmark = pytest.mark.django_db


def test_contactdetails__str():
    """Checks the contact details string representation."""
    contact = ContactDetails(name="PSF", email="psf@ons.gov.uk")
    assert str(contact) == "PSF"
