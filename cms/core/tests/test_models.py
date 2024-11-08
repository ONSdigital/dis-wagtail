from django.test import TestCase

from cms.core.models import ContactDetails


class ContactDetailsTestCase(TestCase):
    """Tests for the ContactDetails model."""

    def test_contactdetails__str(self):
        """Checks the contact details string representation."""
        contact = ContactDetails(name="PSF", email="psf@ons.gov.uk")
        self.assertEqual(str(contact), "PSF")
