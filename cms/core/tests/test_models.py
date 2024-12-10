from django.test import TestCase

from cms.core.models import ContactDetails


class ContactDetailsTestCase(TestCase):
    """Tests for the ContactDetails model."""

    def test_contactdetails__str(self):
        contact = ContactDetails(name="PSF", email="psf@ons.gov.uk")
        self.assertEqual(str(contact), "PSF")

    def test_contactdetails_trims_trailing_whitespace_on_save(self):
        details = ContactDetails(name=" PSF ", email="psf@ons.gov.uk")
        details.save()

        self.assertEqual(details.name, "PSF")
