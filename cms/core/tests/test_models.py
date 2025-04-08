from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils.wagtail_tests import WagtailTestUtils

from cms.core.models import ContactDetails


class ContactDetailsTestCase(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.contact = ContactDetails.objects.create(name="PSF", email="psf@ons.gov.uk")

    def test_contactdetails__str(self):
        self.assertEqual(str(self.contact), "PSF")

    def test_contactdetails_trims_trailing_whitespace_on_save(self):
        details = ContactDetails(name=" Retail ", email="retail@ons.gov.uk")
        details.save()

        self.assertEqual(details.name, "Retail")

    def test_contactdetails_uniqueness_validation__with_name_case_variation(self):
        with self.assertRaisesMessage(IntegrityError, "core_contactdetails_name_unique"):
            ContactDetails.objects.create(name="Psf", email="psf@ons.gov.uk")

    def test_contactdetails_uniqueness_validation__with_email_case_variation(self):
        with self.assertRaisesMessage(IntegrityError, "core_contactdetails_name_unique"):
            ContactDetails.objects.create(name="PSF", email="PSF@ons.gov.uk")

    def test_contactdetails_creation(self):
        self.assertEqual(ContactDetails.objects.count(), 1)
        ContactDetails.objects.create(name="PSF", email="psf.extra@ons.gov.uk")

        self.assertEqual(ContactDetails.objects.count(), 2)

    def test_contactdetails_add_via_ui(self):
        self.login()
        response = self.client.post(
            reverse(ContactDetails.snippet_viewset.get_url_name("add")),  # pylint: disable=no-member
            data={"name": self.contact.name, "email": self.contact.email},
        )

        self.assertContains(response, "Contact details with this Name, Email and Locale already exists.")
        self.assertEqual(ContactDetails.objects.count(), 1)
