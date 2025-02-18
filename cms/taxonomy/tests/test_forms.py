from django.test import TestCase
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from wagtail.models import Page

from cms.standard_pages.models import InformationPage
from cms.home.models import HomePage  # or wherever you define your custom HomePage
from cms.taxonomy.models import Topic


class TestInformationPageIntegration(TestCase):
    def setUp(self):
        super().setUp()

        # 1) Log in with an admin user so we have permission to add pages
        # self.user = self.login()  # if using WagtailPageTests, or do the manual approach:
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser(
            username="testuser", password="testpassword", email="test@example.com"
        )
        self.client.force_login(user)

        # 2) Create or get the actual HomePage (or IndexPage, etc.) so that it’s valid as a parent
        self.root_page = Page.get_root_nodes().first()

        # If your site’s actual homepage is already created in migrations, you might do:
        # self.home_page = HomePage.objects.first()
        # Or if not, create one:
        self.home_page = HomePage(title="Home", slug="homeee")
        self.root_page.add_child(instance=self.home_page)
        self.home_page.save_revision().publish()

        # 3) Set up some Topics with Treebeard
        # self.topic1 = Topic.add_root(instance=Topic(id="t1", title="Topic1"))
        # self.topic2 = Topic.add_root(instance=Topic(id="t2", title="Topic2"))
        self.topic1 = Topic(id="t1", title="Health and life expectancies")
        self.topic1.save_topic()
        self.topic2 = Topic(id="t2", title="Topic2")
        self.topic2.save_topic()

        # 4) Get the real content_type for InformationPage
        content_type = ContentType.objects.get_for_model(InformationPage)
        self.app_label = content_type.app_label  # e.g. "standard_pages"
        self.model_name = content_type.model  # e.g. "informationpage"

    def test_create_information_page_with_duplicates(self):
        # The parent page ID must be the HomePage (allowed parent), not the root
        add_url = reverse("wagtailadmin_pages:add", args=[self.app_label, self.model_name, self.home_page.id])

        post_data = {
            "title": "Info page 1",
            "slug": "info-page-500",
            # Provide the JSON string that Draftail expects:
            "summary": '{"blocks":[{"key":"v3k0g","text":"Info page 1 summary","type":"unstyled","depth":0,"inlineStyleRanges":[],"entityRanges":[],"data":{}}],"entityMap":{}}',
            # If you have other required fields, add them:
            "last_updated": "",
            "content-count": "1",
            "content-0-deleted": "",
            "content-0-order": 0,
            "content-0-type": "heading",
            "content-0-id": "e44ea7b7-9df7-4c1c-870c-76598e5c9706",
            "content-0-value": "Hello world",
            # If your page has optional listing fields, social fields, etc., they can be empty:
            "show_in_menus": "on",
            "page_related_pages-TOTAL_FORMS": "0",
            "page_related_pages-INITIAL_FORMS": "0",
            "page_related_pages-MIN_NUM_FORMS": "0",
            "page_related_pages-MAX_NUM_FORMS": "1000",
            # Required formset management fields for 'topics'
            "topics-TOTAL_FORMS": "1",
            "topics-INITIAL_FORMS": "1",
            "topics-MIN_NUM_FORMS": "0",
            "topics-MAX_NUM_FORMS": "1000",
            # The existing or newly selected topic
            "topics-0-id": "",
            "topics-0-topic": str(self.topic1.pk),
            "topics-0-DELETE": "",
            # ...
            "action-publish": "action-publish",
        }
        # breakpoint()
        response = self.client.post(add_url, post_data)
        # breakpoint()
        if response.status_code == 200:
            # Print out the rendered HTML to see the error messages
            print(response.content.decode())

            # Or check the form's error dictionary if it's passed in the context
            if "form" in response.context:
                print("Form errors:", response.context["form"].errors)

                # Check if there are formset errors too
                for formset_name, formset in response.context["form"].formsets.items():
                    print(f"Errors in formset '{formset_name}':", formset.errors)

        # If creation succeeds, Wagtail typically responds with a 302 redirect
        self.assertEqual(response.status_code, 302, f"Form was not submitted successfully; got {response.status_code}")
        # breakpoint()
        # Now the page should exist
        new_page = InformationPage.objects.get(slug="test-info-page")
        self.assertEqual(new_page.topics.count(), 2, "Duplicates should have been removed")
        self.assertIn(self.topic1.pk, new_page.topics.values_list("topic_id", flat=True))
        self.assertIn(self.topic2.pk, new_page.topics.values_list("topic_id", flat=True))
