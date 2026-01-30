from typing import Any

from django.test import TestCase, override_settings
from wagtail.models import Site
from wagtail_factories import DocumentFactory, ImageFactory

from cms.private_media.constants import Privacy
from cms.standard_pages.models import InformationPage

# TODO: remove when Wagtail updates to django-tasks >= 0.11
TASKS_ENQUEUE_ON_COMMIT = {
    "default": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
        "ENQUEUE_ON_COMMIT": False,
    }
}


class SignalHandlersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = Site.objects.select_related("root_page").first()
        cls.home_page = cls.site.root_page
        cls.test_page = cls.make_information_page([])

    @classmethod
    def make_information_page(cls, content: list[dict[str, Any]]) -> InformationPage:
        """Creates an information page with the provided content value and returns it."""
        instance = InformationPage(title="Test Information Page", summary="Test", content=content)
        cls.home_page.add_child(instance=instance)
        return instance

    def setUp(self):
        self.private_image = ImageFactory()
        self.public_image = ImageFactory(_privacy=Privacy.PUBLIC)
        self.private_document = DocumentFactory()
        self.public_document = DocumentFactory(_privacy=Privacy.PUBLIC)

    def generate_non_media_referencing_content(self) -> list[dict[str, Any]]:
        """Returns a raw StreamField value that includes a heading."""
        return [{"type": "heading", "value": "Test heading"}]

    def generate_media_referencing_content(self) -> list[dict[str, Any]]:
        """Returns a raw StreamField value that includes image and document blocks that
        reference all media created in setUp().
        """
        return [
            {"type": "heading", "value": "Test heading"},
            {"type": "image", "value": {"image": self.private_image.id}},
            {"type": "image", "value": {"image": self.public_image.id}},
            {
                "type": "documents",
                "value": [
                    {
                        "type": "document",
                        "value": {"document": self.private_document.id, "title": "Private document", "description": ""},
                    },
                    {
                        "type": "document",
                        "value": {"document": self.public_document.id, "title": "Public document", "description": ""},
                    },
                ],
            },
        ]

    def assertMediaPrivacy(self, expected_privacy: Privacy):  # pylint: disable=invalid-name
        """Checks that all media created in setup() has the expected privacy, after reloading field
        data from the database.
        """
        self.private_image.refresh_from_db()
        self.assertEqual(self.private_image.privacy, expected_privacy)
        self.public_image.refresh_from_db()
        self.assertEqual(self.public_image.privacy, expected_privacy)
        self.private_document.refresh_from_db()
        self.assertEqual(self.private_document.privacy, expected_privacy)
        self.public_document.refresh_from_db()
        self.assertEqual(self.public_document.privacy, expected_privacy)

    @override_settings(TASKS=TASKS_ENQUEUE_ON_COMMIT)
    def test_publishing_a_page_makes_referenced_media_public(self):
        """Tests the impact of publishing a media-referencing page has on the privacy of referenced media."""
        self.test_page.content = self.generate_media_referencing_content()

        # Publishing the revision should result in all referenced media becoming public
        self.test_page.save_revision().publish()
        self.assertMediaPrivacy(Privacy.PUBLIC)

    @override_settings(TASKS=TASKS_ENQUEUE_ON_COMMIT)
    def test_unpublishing_a_page_makes_referenced_media_private(self):
        """Tests the impact of unpublishing a media-referencing page has on the privacy of referenced media."""
        self.test_page.content = self.generate_media_referencing_content()
        self.test_page.live = True
        self.test_page.save(update_fields=["content", "live"])

        # Unpublishing the page should result in all referenced media becoming private,
        # as it isn't referenced by anything else
        self.test_page.unpublish()
        self.assertMediaPrivacy(Privacy.PRIVATE)

    def test_page_without_references_to_media(self):
        """Tests that pages without any referenced to media can still be published and unpublished without issue."""
        self.test_page.content = self.generate_non_media_referencing_content()
        self.test_page.live = True
        self.test_page.save(update_fields=["content", "live"])

        self.test_page.unpublish()

    @override_settings(TASKS=TASKS_ENQUEUE_ON_COMMIT)
    def test_unpublishing_a_page_when_media_is_referenced_by_a_draft_page(self):
        """Tests the impact of unpublishing a page that references media that is referenced by another draft page."""
        # Publish the first page, so that the reference index is populated, then unpublish it again
        self.test_page.content = self.generate_media_referencing_content()
        self.test_page.save_revision().publish()
        self.test_page.unpublish()

        # The media should be private, since it has no other references
        self.assertMediaPrivacy(Privacy.PRIVATE)

        # Create another page that references the media and publish it
        new_page = self.make_information_page(content=self.test_page.content)
        new_page.save_revision().publish()

        # The media should be public again, since it is referenced by the new page
        self.assertMediaPrivacy(Privacy.PUBLIC)

        # Unpublishing the new page SHOULD result in referenced media becoming private,
        # because it is only referenced by draft pages
        new_page.unpublish()
        self.assertMediaPrivacy(Privacy.PRIVATE)

    @override_settings(TASKS=TASKS_ENQUEUE_ON_COMMIT)
    def test_unpublishing_a_page_when_media_is_referenced_by_a_live_page(self):
        """Tests the impact of unpublishing a page that references media that is referenced by another live page."""
        # Publish the first page, with references to media
        self.test_page.content = self.generate_media_referencing_content()
        self.test_page.save_revision().publish()

        # Create another page that references the media and publish it
        new_page = self.make_information_page(content=self.test_page.content)
        new_page.save_revision().publish()

        # Unpublishing the new page SHOULD NOT result in referenced media becoming private,
        # because it is still referenced by the original live page
        new_page.unpublish()
        self.assertMediaPrivacy(Privacy.PUBLIC)
