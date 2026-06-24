from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from cms.methodology.tests.factories import MethodologyPageFactory
from cms.taxonomy.models import GenericPageToTaxonomyTopic
from cms.taxonomy.tests.factories import TopicFactory


class MethodologyTopicPublishUnpublishTestCase(WagtailTestUtils, TestCase):
    """Regression tests for the duplicate (page, topic) IntegrityError."""

    @classmethod
    def setUpTestData(cls):
        cls.page = MethodologyPageFactory(live=False)
        cls.topic = TopicFactory()

    def setUp(self):
        self.login()

    def _edit_data(self, *, initial_topics):
        data = {
            "title": self.page.title,
            "slug": self.page.slug,
            "summary": rich_text(self.page.summary),
            "publication_date": self.page.publication_date.isoformat(),
            "last_revised_date": self.page.last_revised_date.isoformat(),
            "show_cite_this_page": "on",
            "content": streamfield(
                [("section", {"title": "Test", "content": streamfield([("rich_text", rich_text("text"))])})]
            ),
            "related_pages-TOTAL_FORMS": "0",
            "related_pages-INITIAL_FORMS": "0",
            "related_pages-MIN_NUM_FORMS": "0",
            "related_pages-MAX_NUM_FORMS": "1000",
            "topics-TOTAL_FORMS": "1",
            "topics-INITIAL_FORMS": str(initial_topics),
            "topics-MIN_NUM_FORMS": "0",
            "topics-MAX_NUM_FORMS": "1000",
            # The topic is always submitted id-less: it is never committed to the DB by the
            # live-page draft save, and publishing does not backfill the id into the revision.
            "topics-0-topic": self.topic.pk,
            "topics-0-id": "",
        }
        return nested_form_data(data)

    def _save_draft(self, *, initial_topics):
        return self.client.post(
            reverse("wagtailadmin_pages:edit", args=(self.page.pk,)),
            self._edit_data(initial_topics=initial_topics),
        )

    def test_publish_unpublish_then_save_does_not_duplicate_topic(self):
        # 1. Publish the page
        self.page.save_revision().publish()
        self.page.refresh_from_db()

        # 2. Add the topic and save draft (page is live -> commit=False, topic only in the revision)
        response = self._save_draft(initial_topics=0)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.page.refresh_from_db()
        self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=self.page).count(), 0)

        # 3. Publish with the topic
        self.page.get_latest_revision().publish()
        self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=self.page).count(), 1)

        # 4. Unpublish
        self.page.refresh_from_db()
        self.page.unpublish()

        # 5. Save again - the id-less revision topic must not duplicate the committed row
        self.page.refresh_from_db()
        response = self._save_draft(initial_topics=1)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=self.page).count(), 1)

    def test_repeated_idless_topic_save_does_not_duplicate(self):
        edit_url = reverse("wagtailadmin_pages:edit", args=(self.page.pk,))

        # First save commits the link to the database.
        first = self.client.post(edit_url, self._edit_data(initial_topics=0))
        self.assertEqual(first.status_code, HTTPStatus.FOUND)
        self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=self.page).count(), 1)

        # Second save re-submits the same topic as an id-less row.
        second = self.client.post(edit_url, self._edit_data(initial_topics=0))
        self.assertEqual(second.status_code, HTTPStatus.FOUND)
        self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=self.page).count(), 1)
