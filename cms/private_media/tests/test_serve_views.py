import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest import mock

import time_machine
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.documents import get_document_model
from wagtail.images import get_image_model
from wagtail.images.models import Filter
from wagtail.models import Collection
from wagtail_factories import DocumentFactory, ImageFactory

from cms.bundles.models import BundleTeam
from cms.bundles.tests.factories import BundleFactory, BundlePageFactory
from cms.bundles.tests.utils import create_bundle_viewer
from cms.core.tests.utils import rebuild_references_index
from cms.private_media.constants import Privacy
from cms.standard_pages.tests.factories import InformationPageFactory
from cms.teams.tests.factories import TeamFactory
from cms.workflows.tests.utils import mark_page_as_ready_for_review

FROZEN_TIME = datetime(2026, 1, 1, hour=13, minute=37)


def _build_image_and_document_content(image, document):
    """Build a StreamField section containing the given image and document."""
    return [
        {
            "type": "section",
            "value": {
                "title": "Content",
                "content": [
                    {"type": "image", "value": {"image": image.id}, "id": str(uuid.uuid4())},
                    {
                        "type": "documents",
                        "value": [
                            {
                                "type": "document",
                                "value": {"document": document.id},
                                "id": str(uuid.uuid4()),
                            },
                        ],
                    },
                ],
            },
        }
    ]


class TestImageServeView(TestCase):
    model = get_image_model()

    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)
        cls.private_image = ImageFactory(collection=cls.root_collection)
        cls.public_image = ImageFactory(_privacy=Privacy.PUBLIC, collection=cls.root_collection)
        cls.private_image_renditions = tuple(
            cls.private_image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20")).values()
        )
        cls.public_image_renditions = tuple(
            cls.public_image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20")).values()
        )
        cls.superuser = get_user_model().objects.create(username="superuser", is_superuser=True)

    def setUp(self):
        # Clear potentially invalid 'serve_url' @cached_property values
        for rendition in self.private_image_renditions + self.public_image_renditions:
            rendition.__dict__.pop("serve_url", None)

    def test_serve_private_image(self):
        """Test the serve view behaviour for private image renditions."""
        # If not authenticated, permission checks should fail and a Forbidden response returned
        for rendition in self.private_image_renditions:
            for is_external_env in [True, False]:
                with self.subTest(rendition=rendition, is_external_env=is_external_env) and override_settings(
                    IS_EXTERNAL_ENV=is_external_env
                ):
                    response = self.client.get(rendition.serve_url)
                    self.assertEqual(response.status_code, 403)

        # If authenticated as a superuser, the view should serve the files
        self.client.force_login(self.superuser)
        for rendition in self.private_image_renditions:
            for is_external_env in [True, False]:
                with self.subTest(rendition=rendition, is_external_env=is_external_env) and override_settings(
                    IS_EXTERNAL_ENV=is_external_env
                ):
                    response = self.client.get(rendition.serve_url)
                    self.assertEqual(response.status_code, 403 if is_external_env else 200)

    def test_serve_public_image(self):
        """Test the serve view behaviour for public image renditions."""
        # For public image renditions, the serve view should redirect to the file path or URL.
        for rendition in self.public_image_renditions:
            for is_external_env in [True, False]:
                with self.subTest(rendition=rendition, is_external_env=is_external_env) and override_settings(
                    IS_EXTERNAL_ENV=is_external_env
                ):
                    response = self.client.get(rendition.serve_url)
                    self.assertEqual(response.status_code, 302)

    def test_serve_public_image_with_outdated_file_permissions(self):
        """Test the serve view behaviour for public image renditions with outdated file permissions."""
        self.model.objects.filter(id=self.public_image.id).update(file_permissions_last_set=None)
        self.public_image.refresh_from_db()
        self.assertTrue(self.public_image.has_outdated_file_permissions())
        for rendition in self.public_image_renditions:
            response = self.client.get(rendition.serve_url)
            self.assertEqual(response.status_code, 200)

    def test_serve_with_invalid_signature(self):
        """Test the serve view rejects requests when the signature is invalid."""
        rendition = self.private_image_renditions[0]

        # Generate an otherwise valid `serve_url` with an invalid signature
        with mock.patch("wagtail.images.views.serve.generate_signature", return_value="invalid-signature"):
            serve_url = rendition.serve_url

        # Test the view using the generated `serve_url`
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 400)

    def test_serve_with_invalid_image_id(self):
        """Test the serve view behaviour when the signature is valid but the image ID
        is not recognised.
        """
        rendition = self.public_image_renditions[0]
        original_image_id = self.public_image.id

        # Replace `image_id` value with an invalid one
        self.public_image.id = 9999999

        # Generate an otherwise valid `serve_url` with a reference to a non-existent image ID
        serve_url = rendition.serve_url

        # Undo change to `image_id` to avoid impacting other tests
        self.public_image.id = original_image_id

        # Test the view using the generated `serve_url`
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 404)

    def test_serve_with_invalid_filter_spec(self):
        """Test the serve view behaviour when the filter spec is invalid."""
        rendition = self.public_image_renditions[0]
        original_filter_spec = rendition.filter_spec

        # Replace `filter_spec`` value with an invalid one
        rendition.filter_spec = "invalid-filter-spec"

        # Generate an otherwise valid `serve_url` with an invalid filter spec
        serve_url = rendition.serve_url

        # Undo change to `filter_spec` to avoid impacting other tests
        rendition.filter_spec = original_filter_spec

        # Test the view using the generated `serve_url`
        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 400)


class TestDocumentServeView(TestCase):
    model = get_document_model()

    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)
        cls.private_document = DocumentFactory(collection=cls.root_collection)
        cls.public_document = DocumentFactory(_privacy=Privacy.PUBLIC, collection=cls.root_collection)
        cls.superuser = get_user_model().objects.create(username="superuser", is_superuser=True)

    def test_serve_private_document(self):
        """Test the serve view behaviour for private documents."""
        serve_url = self.private_document.url

        # If not authenticated, permission checks should fail and a Forbidden response returned
        for is_external_env in [True, False]:
            with self.subTest(is_external_env=is_external_env) and override_settings(IS_EXTERNAL_ENV=is_external_env):
                response = self.client.get(serve_url)
                self.assertEqual(response.status_code, 403)

        # If authenticated as a superuser, the view should serve the file
        self.client.force_login(self.superuser)
        for is_external_env in [True, False]:
            with self.subTest(is_external_env=is_external_env) and override_settings(IS_EXTERNAL_ENV=is_external_env):
                response = self.client.get(serve_url)
                self.assertEqual(response.status_code, 403 if is_external_env else 200)

    def test_serve_public_document(self):
        """Test the serve view behaviour for public documents."""
        # For public documents, the serve view should redirect to the file path or URL.
        for is_external_env in [True, False]:
            with self.subTest(is_external_env=is_external_env) and override_settings(IS_EXTERNAL_ENV=is_external_env):
                response = self.client.get(self.public_document.serve_url)
                self.assertEqual(response.status_code, 302)

    def test_serve_public_document_with_outdated_file_permissions(self):
        """Test the serve view behaviour for public documents with outdated file permissions."""
        self.model.objects.filter(id=self.public_document.id).update(file_permissions_last_set=None)
        self.public_document.refresh_from_db()
        self.assertTrue(self.public_document.has_outdated_file_permissions())
        response = self.client.get(self.public_document.url)
        self.assertEqual(response.status_code, 200)

    def test_serve_with_invalid_document_id(self):
        """Test the serve view behaviour when the document ID is not recognised."""
        serve_url = self.private_document.url
        serve_url = serve_url.replace(f"/{self.private_document.id}/", "/9999999/")

        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 404)

    def test_serve_with_invalid_filename(self):
        """Test the serve view behaviour when the document ID is correct, but the filename is not."""
        serve_url = self.private_document.url
        serve_url = serve_url.replace(self.private_document.filename, "invalid-filename.docx")

        response = self.client.get(serve_url)
        self.assertEqual(response.status_code, 404)


class TestPrivateMediaServeViewInBundlePreviewContext(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)
        cls.private_image = ImageFactory(collection=cls.root_collection)
        cls.private_image_rendition = cls.private_image.create_rendition(Filter("width-1024"))
        cls.private_document = DocumentFactory(collection=cls.root_collection)

        cls.content = _build_image_and_document_content(cls.private_image, cls.private_document)
        cls.page = InformationPageFactory(content=cls.content)
        mark_page_as_ready_for_review(cls.page)

        cls.preview_team = TeamFactory(name="Preview Team")
        cls.bundle = BundleFactory(in_review=True)
        BundlePageFactory(parent=cls.bundle, page=cls.page)
        BundleTeam.objects.create(parent=cls.bundle, team=cls.preview_team)

        cls.viewer = create_bundle_viewer()
        cls.viewer.teams.add(cls.preview_team)

        cls.no_access_viewer = create_bundle_viewer("nobundle.viewer")
        cls.no_access_viewer.teams.add(TeamFactory(name="No-access preview team"))

        cls.url_preview_ready = reverse("bundles:preview", args=[cls.bundle.pk, cls.page.pk])

    def setUp(self):
        rebuild_references_index()

    def test_direct_request__gives_no_access__for_viewer_in_bundle_team_because_of_missing_cookie(self):
        self.client.force_login(self.viewer)

        for asset in [self.private_image_rendition, self.private_document]:
            with self.subTest(msg=f"Testing {asset}"):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 403)

    def test_direct_request__gives_no_access__for_viewer_not_in_bundle_team(self):
        self.client.force_login(self.no_access_viewer)

        for asset in [self.private_image_rendition, self.private_document]:
            with self.subTest(msg=f"Testing {asset}"):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 403)

    def test_access_via_bundle_preview__for_viewer_in_bundle_team(self):
        self.client.force_login(self.viewer)

        with time_machine.travel(FROZEN_TIME, tick=False):
            response = self.client.get(self.url_preview_ready)

            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertIn("bundle-preview", self.client.cookies)
            self.assertContains(response, self.private_image_rendition.serve_url)
            self.assertContains(response, self.private_document.serve_url)

        for asset in [self.private_image_rendition, self.private_document]:
            with (
                self.subTest(msg=f"Testing {asset} before cooldown"),
                time_machine.travel(FROZEN_TIME + timedelta(seconds=5), tick=False),
            ):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 200)

            with (
                self.subTest(msg=f"Testing {asset} after cooldown"),
                time_machine.travel(FROZEN_TIME + timedelta(seconds=35), tick=False),
            ):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 403)

    def test_access_via_bundle_preview__for_viewer_not_in_bundle_team(self):
        self.client.force_login(self.no_access_viewer)

        with time_machine.travel(FROZEN_TIME, tick=False):
            response = self.client.get(self.url_preview_ready)

            self.assertEqual(response.status_code, HTTPStatus.FOUND)  # redirects to the admin with an access denied
            self.assertNotIn("bundle-preview", self.client.session)

        for asset in [self.private_image_rendition, self.private_document]:
            with (
                self.subTest(msg=f"Testing {asset} before cooldown"),
                time_machine.travel(FROZEN_TIME + timedelta(seconds=5), tick=False),
            ):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 403)

    def test_access_via_bundle_preview__with_tampered_cookie(self):
        self.client.force_login(self.viewer)

        self.client.get(self.url_preview_ready)
        altered_value = self.client.cookies[settings.BUNDLE_PREVIEW_COOKIE_NAME].value[:-2] + "$$"
        self.client.cookies[settings.BUNDLE_PREVIEW_COOKIE_NAME].set(
            settings.BUNDLE_PREVIEW_COOKIE_NAME, altered_value, altered_value
        )

        for asset in [self.private_image_rendition, self.private_document]:
            with self.subTest(msg=f"Testing {asset}"):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 403)

    def test_access_via_bundle_preview__when_added_to_draft_of_published_page(self):
        # create a new page, and publish
        new_page = InformationPageFactory(
            content=[
                {"type": "section", "value": {"title": "Content", "content": [{"type": "rich_text", "value": "text"}]}}
            ]
        )
        new_page.save_revision().publish()

        # now update its content to reference still private assets
        new_page.content = self.content
        new_page.save_revision()

        # mark as ready for review, and add it to our bundle
        mark_page_as_ready_for_review(new_page)
        BundlePageFactory(parent=self.bundle, page=new_page)

        # now check
        self.client.force_login(self.viewer)

        response = self.client.get(reverse("bundles:preview", args=[self.bundle.pk, new_page.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("bundle-preview", self.client.cookies)
        self.assertContains(response, self.private_image_rendition.serve_url)
        self.assertContains(response, self.private_document.serve_url)

        for asset in [self.private_image_rendition, self.private_document]:
            with self.subTest(msg=f"Testing {asset}"):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 200)

        # create another set of private assets which should not be accessible with a still valid preview cookie
        # becuase they are not part of the page in question
        another_private_image = ImageFactory(collection=self.root_collection)
        another_private_image_rendition = another_private_image.create_rendition(Filter("width-1024"))
        another_private_document = DocumentFactory(collection=self.root_collection)

        for asset in [another_private_image_rendition, another_private_document]:
            with self.subTest(msg=f"Testing private {asset} not in the bundle"):
                response = self.client.get(asset.serve_url)
                self.assertEqual(response.status_code, 403)

    def test_access_via_bundle_preview__multiple_pages_do_not_clobber(self):
        """Previewing a second page should not revoke access to the first page's assets."""
        # Create a second page with different private assets
        other_image = ImageFactory(collection=self.root_collection)
        other_image_rendition = other_image.create_rendition(Filter("width-1024"))
        other_document = DocumentFactory(collection=self.root_collection)

        other_page = InformationPageFactory(content=_build_image_and_document_content(other_image, other_document))
        mark_page_as_ready_for_review(other_page)
        BundlePageFactory(parent=self.bundle, page=other_page)
        rebuild_references_index()

        self.client.force_login(self.viewer)

        with time_machine.travel(FROZEN_TIME, tick=False):
            # Preview the first page
            self.client.get(self.url_preview_ready)
            # Preview the second page (should accumulate, not replace)
            self.client.get(reverse("bundles:preview", args=[self.bundle.pk, other_page.pk]))

        with time_machine.travel(FROZEN_TIME + timedelta(seconds=5), tick=False):
            # Assets from the first page should still be accessible
            for asset in [self.private_image_rendition, self.private_document]:
                with self.subTest(msg=f"First page asset {asset}"):
                    response = self.client.get(asset.serve_url)
                    self.assertEqual(response.status_code, 200)

            # Assets from the second page should also be accessible
            for asset in [other_image_rendition, other_document]:
                with self.subTest(msg=f"Second page asset {asset}"):
                    response = self.client.get(asset.serve_url)
                    self.assertEqual(response.status_code, 200)

    def test_access_via_bundle_preview__per_entry_expiry_is_not_extended_by_refresh(self):
        """A later preview refreshes the cookie but must not extend earlier entries' grants."""
        other_image = ImageFactory(collection=self.root_collection)
        other_image_rendition = other_image.create_rendition(Filter("width-1024"))
        other_document = DocumentFactory(collection=self.root_collection)

        other_page = InformationPageFactory(content=_build_image_and_document_content(other_image, other_document))
        mark_page_as_ready_for_review(other_page)
        BundlePageFactory(parent=self.bundle, page=other_page)
        rebuild_references_index()

        self.client.force_login(self.viewer)

        max_age = settings.BUNDLE_PREVIEW_COOKIE_MAX_AGE

        # Preview the first page at T=0; its entry expires at T=max_age.
        with time_machine.travel(FROZEN_TIME, tick=False):
            self.client.get(self.url_preview_ready)

        # Preview the second page close to (but before) the first entry's expiry.
        # This refreshes the cookie, but the first entry's expires_at should be pinned.
        with time_machine.travel(FROZEN_TIME + timedelta(seconds=max_age - 5), tick=False):
            self.client.get(reverse("bundles:preview", args=[self.bundle.pk, other_page.pk]))

        # Just past the first entry's expiry: first page's assets revoked, second page's still valid.
        with time_machine.travel(FROZEN_TIME + timedelta(seconds=max_age + 5), tick=False):
            for asset in [self.private_image_rendition, self.private_document]:
                with self.subTest(msg=f"First page asset {asset} after its entry expired"):
                    response = self.client.get(asset.serve_url)
                    self.assertEqual(response.status_code, 403)

            for asset in [other_image_rendition, other_document]:
                with self.subTest(msg=f"Second page asset {asset} still within its entry's expiry"):
                    response = self.client.get(asset.serve_url)
                    self.assertEqual(response.status_code, 200)
