from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page
from wagtail.test.utils import WagtailTestUtils
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from cms.articles.tests.factories import ArticleSeriesPageFactory
from cms.methodology.models import MethodologyPage
from cms.methodology.tests.factories import MethodologyPageFactory
from cms.standard_pages.models import InformationPage  # Uses GenericTaxonomyMixin
from cms.standard_pages.tests.factories import InformationPageFactory
from cms.taxonomy.models import GenericPageToTaxonomyTopic, Topic
from cms.taxonomy.tests.factories import TopicFactory
from cms.themes.models import ThemePage  # Uses ExclusiveTaxonomyMixin
from cms.topics.models import TopicPage  # Uses ExclusiveTaxonomyMixin


class TestExclusiveTaxonomyMixin(TestCase, WagtailTestUtils):
    """Tests for ExclusiveTaxonomyMixin:
    - topic is required
    - no two pages (across all ExclusiveTaxonomyMixin subclasses)
    can share the same topic unless they are translations of the same page (not shown here).
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

    def setUp(self):
        self.client.force_login(self.superuser)

        self.root_page = Page.objects.get(id=1)

        # Create normal topics (depth=2) using save_topic()
        self.topic_a = Topic(id="topic-a", title="Topic A")
        Topic.save_new(self.topic_a)

        self.topic_b = Topic(id="topic-b", title="Topic B")
        Topic.save_new(self.topic_b)

    def test_topic_required(self):
        """If .topic is None, ExclusiveTaxonomyMixin.clean() should raise ValidationError
        alongside the default field-level validation error ("This field cannot be blank.").
        """
        theme_page = ThemePage(
            title="Theme page",
            topic=None,  # Will trigger validation error
            summary="My theme page summary",
        )

        with self.assertRaises(ValidationError) as ctx:
            self.root_page.add_child(instance=theme_page)

        error_dict = ctx.exception.message_dict

        self.assertIn("topic", error_dict, "Expected 'topic' key in validation error dict.")

        # We expect two messages: the Django field-level blank error + the Mixin's custom error
        self.assertIn("This field cannot be blank.", error_dict["topic"])
        self.assertIn("A topic is required.", error_dict["topic"])

    def test_exclusivity_within_same_subclass(self):
        """If one ThemePage references topic_a, another ThemePage referencing the same topic
        should fail validation.
        """
        theme_page_1 = ThemePage(title="Theme 1", topic=self.topic_a, summary="My theme page summary")
        self.root_page.add_child(instance=theme_page_1)
        theme_page_1.save()

        theme_page_2 = ThemePage(title="Theme 2", topic=self.topic_a, summary="My theme page summary")

        with self.assertRaises(ValidationError) as ctx:
            self.root_page.add_child(instance=theme_page_2)

        error_dict = ctx.exception.message_dict

        self.assertIn("topic", error_dict, "Expected 'topic' key in validation error dict.")
        self.assertIn("This topic is already linked to another theme or topic page.", error_dict["topic"])

    def test_exclusivity_across_subclasses(self):
        """A ThemePage references topic_a => a TopicPage referencing topic_a should fail validation.
        Because ExclusiveTaxonomyMixin checks all subclasses that share the Mixin.
        """
        theme_page = ThemePage(title="My Theme", topic=self.topic_a, summary="My theme page summary")
        self.root_page.add_child(instance=theme_page)
        theme_page.save()

        topic_page = TopicPage(title="My Topic Page", topic=self.topic_a, summary="My topic page summary")

        with self.assertRaises(ValidationError) as ctx:
            self.root_page.add_child(instance=topic_page)

        error_dict = ctx.exception.message_dict

        self.assertIn("topic", error_dict, "Expected 'topic' key in validation error dict.")
        self.assertIn("This topic is already linked to another theme or topic page.", error_dict["topic"])

    def test_changing_topic_to_already_used_raises_error(self):
        """If a page initially references topic_a, then we try to change
        it to topic_b which is used by another page => error on validation.
        """
        theme_page_1 = ThemePage(title="Theme 1", topic=self.topic_a, summary="My theme page summary")
        self.root_page.add_child(instance=theme_page_1)
        theme_page_1.save()

        theme_page_2 = ThemePage(title="Theme 2", topic=self.topic_b, summary="My theme page summary")
        self.root_page.add_child(instance=theme_page_2)
        theme_page_2.save()

        theme_page_2.topic = self.topic_a

        with self.assertRaises(ValidationError) as ctx:
            theme_page_2.save()

        error_dict = ctx.exception.message_dict

        self.assertIn("topic", error_dict, "Expected 'topic' key in validation error dict.")
        self.assertIn("This topic is already linked to another theme or topic page.", error_dict["topic"])

    def test_changing_topic_to_already_used_raises_error_across_subclasses(self):
        """If a page initially references topic_a, then we try to change
        it to topic_b which is used by another page across subclasses => error on validation.
        """
        theme_page = ThemePage(title="My Theme", topic=self.topic_a, summary="My theme page summary")
        self.root_page.add_child(instance=theme_page)
        theme_page.save()

        topic_page = TopicPage(title="My Topic Page", topic=self.topic_b, summary="My topic page summary")
        self.root_page.add_child(instance=topic_page)
        topic_page.save()

        topic_page.topic = self.topic_a

        with self.assertRaises(ValidationError) as ctx:
            topic_page.save()

        error_dict = ctx.exception.message_dict

        self.assertIn("topic", error_dict, "Expected 'topic' key in validation error dict.")
        self.assertIn("This topic is already linked to another theme or topic page.", error_dict["topic"])


class TestGenericTaxonomyMixin(TestCase, WagtailTestUtils):
    """Tests for GenericTaxonomyMixin using the InformationPage model.

    - we can add multiple topics to the same page
    - there's no exclusivity requirement
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = cls.create_superuser(username="admin")

    def setUp(self):
        self.client.force_login(self.superuser)

        self.root_page = Page.objects.get(id=1)

        self.topic_c = Topic(id="topic-c", title="Topic C")
        Topic.save_new(self.topic_c)

        self.topic_d = Topic(id="topic-d", title="Topic D")
        Topic.save_new(self.topic_d)

    def test_can_assign_multiple_topics_to_information_page(self):
        """For GenericTaxonomyMixin, we do not enforce exclusive usage of a topic.
        We'll create an InformationPage and assign multiple topics.
        """
        info_page = InformationPage(title="My Info Page", summary="My info page summary")
        self.root_page.add_child(instance=info_page)
        info_page.save()

        GenericPageToTaxonomyTopic.objects.create(page=info_page, topic=self.topic_c)
        GenericPageToTaxonomyTopic.objects.create(page=info_page, topic=self.topic_d)

        self.assertEqual(info_page.topics.count(), 2, "Should be able to assign 2 distinct topics")

    def test_same_topic_on_multiple_information_pages(self):
        """The same topic can appear on multiple InformationPages without error.
        There's no exclusivity check in GenericTaxonomyMixin.
        """
        info_page1 = InformationPage(title="Info Page 1", summary="My info page summary")
        self.root_page.add_child(instance=info_page1)
        info_page1.save()
        GenericPageToTaxonomyTopic.objects.create(page=info_page1, topic=self.topic_c)

        info_page2 = InformationPage(title="Info Page 2", summary="My info page summary")
        self.root_page.add_child(instance=info_page2)
        info_page2.save()
        GenericPageToTaxonomyTopic.objects.create(page=info_page2, topic=self.topic_c)

        self.assertEqual(info_page1.topics.count(), 1)
        self.assertEqual(info_page2.topics.count(), 1)

    def test_no_exclusivity_validation(self):
        """GenericTaxonomyMixin doesn't do a .clean() check for uniqueness across pages.
        So we expect zero ValidationError if multiple pages share the same topic.
        """
        info_page1 = InformationPage(title="Info Page 1", summary="My info page summary")
        self.root_page.add_child(instance=info_page1)
        info_page1.save()
        GenericPageToTaxonomyTopic.objects.create(page=info_page1, topic=self.topic_c)

        info_page2 = InformationPage(title="Info Page 2", summary="My info page summary")
        self.root_page.add_child(instance=info_page2)
        info_page2.save()
        GenericPageToTaxonomyTopic.objects.create(page=info_page2, topic=self.topic_c)

        try:
            info_page1.full_clean()
            info_page2.full_clean()
        except ValidationError:
            self.fail("Expected no ValidationError for shared topics in GenericTaxonomyMixin.")


class TestGenericTaxonomyMixinIntegrityError(WagtailTestUtils, TestCase):
    """Regression tests for the duplicate (page, topic) IntegrityError."""

    @classmethod
    def setUpTestData(cls):
        cls.pages = {
            MethodologyPageFactory(live=False),
            InformationPageFactory(live=False),
            ArticleSeriesPageFactory(live=False),
        }
        cls.topic = TopicFactory()

    def setUp(self):
        self.login()

    def _edit_data(self, page, *, initial_topics=0):
        data = {
            "title": page.title,
            "slug": page.slug,
            "summary": rich_text(page.summary),
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
        if isinstance(page, MethodologyPage):
            data["publication_date"] = page.publication_date.isoformat()
            data["last_revised_date"] = page.last_revised_date.isoformat()
        return nested_form_data(data)

    def _save_draft(self, page, *, initial_topics=0):
        return self.client.post(
            reverse("wagtailadmin_pages:edit", args=(page.pk,)),
            self._edit_data(page, initial_topics=initial_topics),
        )

    def test_publish_unpublish_then_save_does_not_duplicate_topic(self):
        for page in self.pages:
            with self.subTest(page_type=page.__class__):
                # 1. Publish the page
                page.save_revision().publish()
                page.refresh_from_db()

                # 2. Add the topic and save draft (page is live -> commit=False, topic only in the revision)
                response = self._save_draft(page)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
                page.refresh_from_db()
                self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=page).count(), 0)

                # 3. Publish with the topic
                page.get_latest_revision().publish()
                self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=page).count(), 1)

                # 4. Unpublish
                page.refresh_from_db()
                page.unpublish()

                # 5. Save again - the id-less revision topic must not duplicate the committed row
                page.refresh_from_db()

                try:
                    response = self._save_draft(page, initial_topics=1)
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)
                    self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=page).count(), 1)
                except IntegrityError:
                    self.fail(f"IntegrityError raised when saving id-less topic for {page.__class__.__name__}.")

    def test_repeated_idless_topic_save_does_not_duplicate(self):
        for page in self.pages:
            with self.subTest(page_type=page.__class__):
                edit_url = reverse("wagtailadmin_pages:edit", args=(page.pk,))

                # First save commits the link to the database.
                first = self.client.post(edit_url, self._edit_data(page))
                self.assertEqual(first.status_code, HTTPStatus.FOUND)
                self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=page).count(), 1)
                try:
                    # Second save re-submits the same topic as an id-less row.
                    second = self.client.post(edit_url, self._edit_data(page))
                    self.assertEqual(second.status_code, HTTPStatus.FOUND)
                    self.assertEqual(GenericPageToTaxonomyTopic.objects.filter(page=page).count(), 1)
                except IntegrityError:
                    self.fail(f"IntegrityError raised when saving id-less topic for {page.__class__.__name__}.")
