from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from wagtail.documents import get_document_model
from wagtail.models import Collection, Site
from wagtail_factories import DocumentFactory, SiteFactory

from cms.private_media.constants import Privacy
from cms.private_media.managers import PrivateDocumentManager
from cms.private_media.models import PrivateDocumentMixin

from .utils import PURGED_URLS


class TestModelConfiguration(SimpleTestCase):
    def test_document_model_using_private_document_mixin(self):
        """Verify that the document model correctly inherits from PrivateDocumentMixin.
        And that the manager is a subclass of PrivateDocumentManager.
        """
        document_model = get_document_model()
        self.assertTrue(issubclass(document_model, PrivateDocumentMixin))
        self.assertIsInstance(document_model.objects, PrivateDocumentManager)


class TestDocumentModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)

    def test_private_document(self):
        """Test the behaviour of private documents:
        - Verify default privacy settings.
        - Test privacy change tracking.
        - Ensure file permission updates are handled correctly.
        - Check file permission outdated status.
        """
        with self.assertLogs("cms.private_media.bulk_operations", level="DEBUG") as logs:
            document = DocumentFactory(collection=self.root_collection)

        # Documents should be 'private' by default
        self.assertIs(document.privacy, Privacy.PRIVATE)
        self.assertTrue(document.is_private)
        self.assertFalse(document.is_public)

        # Attempts to set file permissions on save should have failed gracefully,
        # since the default file backend doesn't support it
        self.assertEqual(
            logs.output,
            [
                (
                    "DEBUG:cms.private_media.bulk_operations:FileSystemStorage does not support setting of individual "
                    f"file permissions to private, so skipping for: {document.file.name}."
                )
            ],
        )

        # File permissions should be considered up-to-date
        self.assertFalse(document.file_permissions_are_outdated())

        # Setting privacy to the same value should not trigger an update to 'privacy_last_changed
        value_before = document.privacy_last_changed
        document.privacy = Privacy.PRIVATE
        self.assertEqual(document.privacy_last_changed, value_before)

        # Setting privacy to a different value should triggered an update to 'privacy_last_changed'
        document.privacy = Privacy.PUBLIC
        self.assertGreater(document.privacy_last_changed, value_before)

        # File permissions should now be considered outdated
        self.assertTrue(document.file_permissions_are_outdated())

        # Resaving should trigger an update to file permissions and the 'file_permissions_last_set'
        # timestamp, resolving the issue
        document.save()
        self.assertFalse(document.file_permissions_are_outdated())

    def test_public_document(self):
        """Test the behaviour of public documents:
        - Verify public privacy settings.
        - Test privacy change tracking.
        - Ensure file permission updates are handled correctly.
        - Check file permission outdated status.
        """
        with self.assertLogs("cms.private_media.bulk_operations", level="DEBUG") as logs:
            document = DocumentFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection)

        # This document should be 'public'
        self.assertIs(document.privacy, Privacy.PUBLIC)
        self.assertTrue(document.is_public)
        self.assertFalse(document.is_private)

        # Attempts to set file permissions on save should have failed gracefully,
        # since the default file backend doesn't support it
        self.assertEqual(
            logs.output,
            [
                (
                    "DEBUG:cms.private_media.bulk_operations:FileSystemStorage does not support setting of individual "
                    f"file permissions to public, so skipping for: {document.file.name}."
                )
            ],
        )

        # File permissions should be considered up-to-date
        self.assertFalse(document.file_permissions_are_outdated())

        # Setting privacy to the same value should not trigger an update to 'privacy_last_changed
        value_before = document.privacy_last_changed
        document.privacy = Privacy.PUBLIC
        self.assertEqual(document.privacy_last_changed, value_before)

        # Setting privacy to a different value should triggered an update to 'privacy_last_changed'
        document.privacy = Privacy.PRIVATE
        self.assertGreater(document.privacy_last_changed, value_before)

        # File permissions should now be considered outdated
        self.assertTrue(document.file_permissions_are_outdated())

        # Resaving should trigger an update to file permissions and the 'file_permissions_last_set'
        # timestamp, resolving the issue
        document.save()
        self.assertFalse(document.file_permissions_are_outdated())

    def test_invalid_privacy_value_raises_value_error(self):
        """Verify that attempting to create a document with an invalid privacy value raises ValueError."""
        with self.assertRaises(ValueError):
            DocumentFactory(_privacy="invalid", collection=self.root_collection)

    def test_get_privacy_controlled_serve_urls(self):
        """Test the behaviour of PrivateImageMixin.get_privacy_controlled_serve_urls."""
        default_site = Site.objects.get(is_default_site=True)
        site_2 = SiteFactory(hostname="foo.com", port=443)
        sites = [default_site, site_2]

        document = DocumentFactory(collection=self.root_collection)
        self.assertEqual(
            list(document.get_privacy_controlled_serve_urls(sites)),
            [
                f"http://localhost{document.url}",
                f"https://foo.com{document.url}",
            ],
        )

        # If no sites are provided, the result should be empty
        with self.assertNumQueries(0):
            self.assertFalse(list(document.get_privacy_controlled_serve_urls([])))

    def test_get_privacy_controlled_file_urls(self):
        """Test the behaviour of PrivateImageMixin.get_privacy_controlled_file_urls."""
        document = DocumentFactory(collection=self.root_collection)

        # FileSystemStorage returns relative URLs for files only, so the return value should be empty
        self.assertFalse(list(document.get_privacy_controlled_file_urls()))

        # However, if the storage backend returns fully-fledged URLs, those values should be
        # included in the return value
        def domain_prefixed_url(name: str) -> str:
            """Replacement for FileSystemStorage.url() that returns fully-fledged URLs."""
            return f"https://media.example.com/{name}"

        with mock.patch("django.core.files.storage.FileSystemStorage.url", side_effect=domain_prefixed_url):
            self.assertEqual(
                list(document.get_privacy_controlled_file_urls()),
                [
                    f"https://media.example.com/{document.file.name}",
                ],
            )

    @override_settings(
        STORAGES={"default": {"BACKEND": "cms.private_media.storages.DummyPrivacySettingFileSystemStorage"}}
    )
    def test_file_permission_setting_success(self):
        """Test successful file permission setting using DummyPrivacySettingFileSystemStorage:
        - Verify permissions are set correctly for both public and private documents.
        - Ensure no debug logs are generated during successful operation.
        """
        with self.assertNoLogs("cms.private_media.bulk_operations", level="DEBUG"):
            private_document = DocumentFactory(collection=self.root_collection)
            public_document = DocumentFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection)

        self.assertFalse(private_document.file_permissions_are_outdated())
        self.assertFalse(public_document.file_permissions_are_outdated())

    @override_settings(
        STORAGES={"default": {"BACKEND": "cms.private_media.storages.DummyPrivacySettingFileSystemStorage"}}
    )
    @mock.patch("cms.private_media.storages.DummyPrivacySettingFileSystemStorage.make_private", return_value=False)
    @mock.patch("cms.private_media.storages.DummyPrivacySettingFileSystemStorage.make_public", return_value=False)
    def test_file_permission_setting_failure(self, mock_make_public, mock_make_private):
        """Test handling of file permission setting failures:
        - Mock failed permission settings for both public and private documents.
        - Verify documents are marked as having outdated permissions.
        - Ensure correct storage methods are called.
        """
        with self.assertNoLogs("cms.private_media.bulk_operations", level="DEBUG"):
            private_document = DocumentFactory(collection=self.root_collection)
            public_document = DocumentFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection)

        mock_make_private.assert_called_once_with(private_document.file)
        self.assertTrue(private_document.file_permissions_are_outdated())
        mock_make_public.assert_called_once_with(public_document.file)
        self.assertTrue(public_document.file_permissions_are_outdated())


@override_settings(
    WAGTAILFRONTENDCACHE={
        "default": {
            "BACKEND": "cms.private_media.tests.utils.MockFrontEndCacheBackend",
        },
    }
)
class TestPrivateDocumentManager(TestCase):
    model = get_document_model()

    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)

    def setUp(self):
        # Create six documents (a mix of private and public)
        self.private_documents = []
        self.public_documents = []
        for _ in range(3):
            self.private_documents.append(DocumentFactory(collection=self.root_collection))
            self.public_documents.append(DocumentFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection))
        PURGED_URLS.clear()

    def test_bulk_make_public(self):
        """Test the behaviour of PrivateDocumentManager.bulk_make_public()."""
        # Three documents are already public, so only three should be updated
        with self.assertNumQueries(3):
            # Query summary:
            # 1. to fetch the documents
            # 2. to save updates
            # 3. to fetch sites to facilitate cache purging
            self.assertEqual(self.model.objects.bulk_make_public(self.model.objects.all()), 3)

        # Serve URLs for private documents should have been purged as part of the update
        for obj in self.private_documents:
            self.assertIn("http://localhost" + obj.url, PURGED_URLS)

        # Verify all images are now public
        for obj in self.model.objects.only("_privacy", "file_permissions_last_set", "privacy_last_changed"):
            self.assertIs(obj.privacy, Privacy.PUBLIC)
            self.assertFalse(obj.file_permissions_are_outdated())

        # Another attempt should result in no updates
        with self.assertNumQueries(1):
            self.assertEqual(self.model.objects.bulk_make_public(self.model.objects.all()), 0)

    def test_bulk_make_private(self):
        """Test the behaviour of PrivateDocumentManager.bulk_make_private()."""
        # Three images are already private, so only three should be updated
        with self.assertNumQueries(3):
            # Query summary:
            # 1. to fetch the documents
            # 2. to save updates
            # 3. to fetch sites to facilitate cache purging
            self.assertEqual(self.model.objects.bulk_make_private(self.model.objects.all()), 3)

        # Serve URLs for public documents should have been purged as part of the update
        for obj in self.public_documents:
            self.assertIn("http://localhost" + obj.url, PURGED_URLS)

        # Verify all images are now private
        for image in self.model.objects.only("_privacy", "file_permissions_last_set", "privacy_last_changed"):
            self.assertIs(image.privacy, Privacy.PRIVATE)
            self.assertFalse(image.file_permissions_are_outdated())

        # Another attempt should result in no updates
        with self.assertNumQueries(1):
            # Query summary:
            # 1. to fetch the documents
            self.assertEqual(self.model.objects.bulk_make_private(self.model.objects.all()), 0)


class TestDocumentServeView(TestCase):
    model = get_document_model()

    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)
        cls.private_document = DocumentFactory(collection=cls.root_collection)
        cls.public_document = DocumentFactory(_privacy=Privacy.PUBLIC, collection=cls.root_collection)
        cls.superuser = get_user_model().objects.create(username="superuser", is_superuser=True)

    def test_private_document(self):
        """Test the serve view behaviour for private documents."""
        # If not authenticated, permission checks should fail and a Forbidden response returned
        response = self.client.get(self.private_document.url)
        self.assertEqual(response.status_code, 403)

        # If authenticated as a superuser, the view should serve the files
        self.client.force_login(self.superuser)
        response = self.client.get(self.private_document.url)
        self.assertEqual(response.status_code, 200)

    def test_public_document(self):
        """Test the serve view behaviour for public documents."""
        # For public documents, the serve view should redirect to the file URL.
        response = self.client.get(self.public_document.url)
        self.assertEqual(response.status_code, 200)

        # This remains the same for public documents, regardless of whether
        # document.file_permissions_are_outdated() returns True
        self.model.objects.filter(id=self.public_document.id).update(file_permissions_last_set=None)
        self.public_document.refresh_from_db()
        self.assertTrue(self.public_document.file_permissions_are_outdated())
        response = self.client.get(self.public_document.url)
        self.assertEqual(response.status_code, 200)