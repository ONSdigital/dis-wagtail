from django.db import IntegrityError
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

    def test_contactdetails_uniqueness_validation__with_name_case_variation(self):
        with self.assertRaisesMessage(IntegrityError, "core_contactdetails_name_unique"):
            ContactDetails.objects.create(name="PSF", email="PSF@ons.gov.uk")
            ContactDetails.objects.create(name="Psf", email="PSF@ons.gov.uk")

    def test_contactdetails_uniqueness_validation__with_email_case_variation(self):
        with self.assertRaisesMessage(IntegrityError, "core_contactdetails_name_unique"):
            ContactDetails.objects.create(name="PSF", email="PSF@ons.gov.uk")
            ContactDetails.objects.create(name="PSF", email="psf@ons.gov.uk")

    def test_contactdetails_creation(self):
        self.assertFalse(ContactDetails.objects.all().exists())
        ContactDetails.objects.create(name="PSF", email="psf@ons.gov.uk")
        ContactDetails.objects.create(name="PSF", email="psf.extra@ons.gov.uk")

        self.assertEqual(ContactDetails.objects.count(), 2)
