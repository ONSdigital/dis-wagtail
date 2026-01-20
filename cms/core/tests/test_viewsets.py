from django.test import TestCase
from django.urls import reverse
from wagtail.models import Locale
from wagtail.test.utils import WagtailTestUtils

from cms.core.tests.factories import ContactDetailsFactory, GlossaryTermFactory
from cms.core.tests.utils import rebuild_internal_search_index


class TestContactDetailsChooserViewSet(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.contact = ContactDetailsFactory(name="First term", email="first@term.space")
        cls.contact_cy = ContactDetailsFactory(
            name="Cyswllt cyntaf", email="first@term.space", locale=Locale.objects.get(language_code="cy")
        )

        chooser_viewset = cls.contact.snippet_viewset.chooser_viewset
        cls.chooser_url = reverse(chooser_viewset.get_url_name("choose"))
        cls.chooser_results_url = reverse(chooser_viewset.get_url_name("choose_results"))

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_chooser_viewset(self):
        response = self.client.get(self.chooser_url)

        self.assertContains(response, "Locale")
        self.assertContains(response, "English")
        self.assertContains(response, "Welsh")

        self.assertContains(response, "Name")
        self.assertContains(response, "Email")
        self.assertContains(response, "Phone")
        self.assertContains(response, self.contact.name)
        self.assertContains(response, self.contact.email)
        self.assertContains(response, self.contact_cy.name)
        self.assertContains(response, self.contact_cy.email)

    def test_chooser_search(self):
        rebuild_internal_search_index()
        response = self.client.get(f"{self.chooser_results_url}?q=first")

        self.assertContains(response, self.contact.name)
        self.assertContains(response, self.contact_cy.name)

        response = self.client.get(f"{self.chooser_results_url}?q=first@term.space&locale=cy")

        self.assertContains(response, self.contact_cy.name)
        self.assertNotContains(response, self.contact.name)

    def test_chooser__no_results(self):
        response = self.client.get(f"{self.chooser_results_url}?q=foo")
        self.assertContains(response, 'Sorry, no snippets match "<em>foo</em>"', html=True)


class TestGlossaryTermChooserViewSet(WagtailTestUtils, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

        cls.term = GlossaryTermFactory(name="First term", definition="something")
        cls.term_cy = GlossaryTermFactory(
            name="Cyswllt cyntaf", definition="something else", locale=Locale.objects.get(language_code="cy")
        )

        chooser_viewset = cls.term.snippet_viewset.chooser_viewset
        cls.chooser_url = reverse(chooser_viewset.get_url_name("choose"))
        cls.chooser_results_url = reverse(chooser_viewset.get_url_name("choose_results"))

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_chooser_viewset(self):
        response = self.client.get(self.chooser_url)

        self.assertContains(response, "Locale")
        self.assertContains(response, "English")
        self.assertContains(response, "Welsh")

        self.assertContains(response, "Name")
        self.assertContains(response, self.term.name)
        self.assertContains(response, self.term_cy.name)

    def test_chooser_search(self):
        rebuild_internal_search_index()
        response = self.client.get(f"{self.chooser_results_url}?q=first")

        self.assertContains(response, self.term.name)
        self.assertNotContains(response, self.term_cy.name)

        response = self.client.get(f"{self.chooser_results_url}?q=something&locale=cy")

        self.assertContains(response, self.term_cy.name)
        self.assertNotContains(response, self.term.name)

    def test_chooser__no_results(self):
        response = self.client.get(f"{self.chooser_results_url}?q=foo")
        self.assertContains(response, 'Sorry, no snippets match "<em>foo</em>"', html=True)
