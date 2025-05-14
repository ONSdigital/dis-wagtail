import http

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils

from cms.standard_pages.models import InformationPage
from cms.taxonomy.models import Topic


class TestInformationPageIntegration(TestCase, WagtailTestUtils):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

    def setUp(self):
        super().setUp()

        self.client.force_login(self.superuser)

        self.root_page = Page.get_root_nodes().first()

        self.topic1 = Topic(id="t1", title="Health and life expectancies")
        Topic.save_new(self.topic1)

        self.topic2 = Topic(id="t2", title="Finance and economy")
        Topic.save_new(self.topic2)

        content_type = ContentType.objects.get_for_model(InformationPage)
        self.app_label = content_type.app_label  # e.g. "standard_pages"
        self.model_name = content_type.model  # e.g. "informationpage"

    def test_create_information_page_with_duplicates(self):
        """When creating an InformationPage, the form should remove duplicate topics added.
        This test is to check our custom forms clean method.
        """
        # The parent page ID must be the HomePage (allowed parent), not the root
        add_url = reverse(
            "wagtailadmin_pages:add", args=[self.app_label, self.model_name, self.root_page.get_children()[0].id]
        )

        post_data = {
            "title": "Info page 1",
            "slug": "info-page-1",
            # Provide the JSON string that Draftail expects:
            "summary": '{"blocks":[{"key":"v3k0g","text":"Info page 1 summary","type":"unstyled","depth":0,'
            '"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}',
            "last_updated": "",
            "content-count": "1",
            "content-0-deleted": "",
            "content-0-order": 0,
            "content-0-type": "heading",
            "content-0-id": "e44ea7b7-9df7-4c1c-870c-76598e5c9706",
            "content-0-value": "Hello world",
            "show_in_menus": "on",
            "page_related_pages-TOTAL_FORMS": "0",
            "page_related_pages-INITIAL_FORMS": "0",
            "page_related_pages-MIN_NUM_FORMS": "0",
            "page_related_pages-MAX_NUM_FORMS": "1000",
            # Required formset management fields for 'topics'
            "topics-TOTAL_FORMS": "2",
            "topics-INITIAL_FORMS": "2",
            "topics-MIN_NUM_FORMS": "0",
            "topics-MAX_NUM_FORMS": "1000",
            # The existing or newly selected topic
            "topics-0-id": "",
            "topics-0-topic": str(self.topic1.pk),
            "topics-0-DELETE": "",
            "topics-1-id": "",
            "topics-1-topic": str(self.topic2.pk),
            "topics-1-DELETE": "",
            "topics-2-id": "",
            "topics-2-topic": str(self.topic2.pk),
            "topics-2-DELETE": "",
            "action-publish": "action-publish",
        }
        response = self.client.post(add_url, post_data)

        # If creation succeeds, Wagtail responds with a 302 redirect
        self.assertEqual(
            response.status_code,
            http.HTTPStatus.FOUND,
            f"Form was not submitted successfully; got {response.status_code}",
        )
        new_page = InformationPage.objects.get(slug="info-page-1", locale=self.root_page.locale)

        self.assertEqual(new_page.topics.count(), 2, "Duplicates should have been removed")
        self.assertIn(self.topic1.pk, new_page.topics.values_list("topic_id", flat=True))
        self.assertIn(self.topic2.pk, new_page.topics.values_list("topic_id", flat=True))
