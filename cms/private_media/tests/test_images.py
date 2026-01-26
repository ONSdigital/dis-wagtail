from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from wagtail.images import get_image_model
from wagtail.images.models import Filter
from wagtail.models import Collection, Site
from wagtail_factories import ImageFactory, SiteFactory

from cms.private_media.constants import Privacy
from cms.private_media.managers import PrivateImageManager
from cms.private_media.models import AbstractPrivateRendition, PrivateImageMixin

from .utils import PURGED_URLS

# TODO: remove when Wagtail updates to django-tasks >= 0.11
TASKS_ENQUEUE_ON_COMMIT = {
    "default": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
        "ENQUEUE_ON_COMMIT": False,
    }
}


class TestModelConfiguration(SimpleTestCase):
    def test_image_model_using_private_image_mixin(self):
        """Verify that the configured image model inherits from PrivateImageMixin."""
        image_model = get_image_model()
        self.assertTrue(issubclass(image_model, PrivateImageMixin))
        self.assertIsInstance(image_model.objects, PrivateImageManager)

    def test_rendition_model_using_abstract_private_rendition(self):
        """Verify that the configured rendition model inherits from AbstractPrivateRendition."""
        rendition_model = get_image_model().get_rendition_model()
        self.assertTrue(issubclass(rendition_model, AbstractPrivateRendition))


class TestImageModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)

    def test_private_image(self):
        """Test the behaviour of private images:
        - Verify that images are created as PRIVATE by default.
        - Verify that file permission states are updated on save to reflect image privacy.
        - Verify that privacy change tracking works correctly.
        """
        # Attempts to set file permissions on save should have failed gracefully,
        # since the default file backend doesn't support it
        with self.assertLogs("cms.private_media.storages", level="INFO") as logs:
            image = ImageFactory(collection=self.root_collection)

        # Images should be 'private' by default
        self.assertIs(image.privacy, Privacy.PRIVATE)
        self.assertTrue(image.is_private)
        self.assertFalse(image.is_public)

        # Attempts to set file permissions on save should have failed gracefully
        self.assertEqual(
            logs.output,
            [
                (
                    "INFO:cms.private_media.storages:Simulating private permission setting for file "
                    f"'{image.file.name}'. No actual changes applied."
                )
            ],
        )

        # File permissions should be considered up-to-date
        self.assertFalse(image.has_outdated_file_permissions())

        # Setting privacy to the same value should not trigger an update to 'privacy_last_changed
        value_before = image.privacy_last_changed
        image.privacy = Privacy.PRIVATE
        self.assertEqual(image.privacy_last_changed, value_before)

        # Setting privacy to a different value should triggered an update to 'privacy_last_changed'
        image.privacy = Privacy.PUBLIC
        self.assertGreater(image.privacy_last_changed, value_before)

        # File permissions should now be considered outdated
        self.assertTrue(image.has_outdated_file_permissions())

        # Resaving should trigger an update to file permissions and the 'file_permissions_last_set'
        # timestamp, resolving the issue
        image.save()
        self.assertFalse(image.has_outdated_file_permissions())

    def test_private_image_renditions(self):
        """Test that private image renditions use serve URLs instead of direct file URLs."""
        image = ImageFactory(collection=self.root_collection)
        renditions = image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20"))
        self.assertEqual(len(renditions), 2)

        # For private images, rendition.url should return a serve URL
        for rendition in renditions.values():
            self.assertEqual(rendition.url, rendition.serve_url)
            # And cache keys should include 'private'
            self.assertIn("-private-", rendition.get_cache_key())

    def test_public_image(self):
        """Test the behaviour of public images.
        - Verify that images can be created as PUBLIC.
        - Verify that file permission states are updated on save to reflect image privacy.
        - Verify that privacy change tracking works correctly.
        - Graceful handling of unsupported storage backends.
        """
        # Attempts to set file permissions on save should have failed gracefully,
        # since the default file backend doesn't support it
        with self.assertLogs("cms.private_media.storages", level="INFO") as logs:
            image = ImageFactory(_privacy=Privacy.PUBLIC)

        # This image should be 'public'
        self.assertIs(image.privacy, Privacy.PUBLIC)
        self.assertTrue(image.is_public)
        self.assertFalse(image.is_private)

        # Attempts to set file permissions on save should have failed gracefully
        self.assertEqual(
            logs.output,
            [
                (
                    "INFO:cms.private_media.storages:Simulating public permission setting for file "
                    f"'{image.file.name}'. No actual changes applied."
                )
            ],
        )

        # File permissions should be considered up-to-date
        self.assertFalse(image.has_outdated_file_permissions())

        # Setting privacy to the same value should not trigger an update to 'privacy_last_changed
        value_before = image.privacy_last_changed
        image.privacy = Privacy.PUBLIC
        self.assertEqual(image.privacy_last_changed, value_before)

        # Setting privacy to a different value should triggered an update to 'privacy_last_changed'
        image.privacy = Privacy.PRIVATE
        self.assertGreater(image.privacy_last_changed, value_before)

        # File permissions should now be considered outdated
        self.assertTrue(image.has_outdated_file_permissions())

        # Resaving should trigger an update to file permissions and the 'file_permissions_last_set'
        # timestamp, resolving the issue
        image.save()
        self.assertFalse(image.has_outdated_file_permissions())

    def test_public_image_renditions(self):
        """Test rendition.url behaviour for public image renditions:
        - Public images with up-to-date permissions use direct file URLs.
        - Falls back to serve URLs when permissions are outdated.
        """
        image = ImageFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection)
        renditions = image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20"))
        self.assertEqual(len(renditions), 2)

        # For public images with up-to-date file permissions, rendition.url should return the file url
        for rendition in renditions.values():
            self.assertEqual(rendition.url, rendition.file.url)
            # And cache keys should include 'public'
            self.assertIn("-public-", rendition.get_cache_key())

        # However, if the file permissions are outdated, rendition.url should return a serve URL
        with mock.patch(
            "cms.private_media.models.PrivateMediaMixin.has_outdated_file_permissions",
            return_value=True,
        ):
            for rendition in renditions.values():
                self.assertEqual(rendition.url, rendition.serve_url)

    def test_get_privacy_controlled_serve_urls(self):
        """Test the behaviour of PrivateImageMixin.get_privacy_controlled_serve_urls."""
        default_site = Site.objects.get(is_default_site=True)
        site_2 = SiteFactory(hostname="foo.com", port=443)
        sites = [default_site, site_2]

        # If an image has no renditions, the result should be empty
        image = ImageFactory(collection=self.root_collection)
        self.assertFalse(list(image.get_privacy_controlled_serve_urls(sites)))

        # If an image has renditions, the result should be a list of serve URLs, prefixed
        # with the root url for each supplied site
        renditions = image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20"))
        expected_result = []
        for base_url in [site.root_url for site in sites]:
            for rendition in renditions.values():
                expected_result.append(f"{base_url}{rendition.url}")
        with self.assertNumQueries(1):
            self.assertEqual(list(image.get_privacy_controlled_serve_urls(sites)), expected_result)

        # If no sites are provided, the result should be empty
        with self.assertNumQueries(0):
            self.assertFalse(list(image.get_privacy_controlled_serve_urls([])))

    def test_get_privacy_controlled_file_urls(self):
        """Test the behaviour of PrivateImageMixin.get_privacy_controlled_file_urls."""
        image = ImageFactory(collection=self.root_collection)
        renditions = image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20"))

        # FileSystemStorage returns relative URLs for files only, so the return value should be empty,
        # even if renditions exist
        self.assertFalse(list(image.get_privacy_controlled_file_urls()))

        # However, if the storage backend returns fully-fledged URLs, those values should be
        # included in the return value

        def domain_prefixed_url(name: str) -> str:
            """Replacement for FileSystemStorage.url() that returns fully-fledged URLs."""
            return f"https://media.example.com/{name}"

        with mock.patch(
            "django.core.files.storage.FileSystemStorage.url",
            side_effect=domain_prefixed_url,
        ):
            expected_result = [f"https://media.example.com/{image.file.name}"]
            for rendition in renditions.values():
                expected_result.append(f"https://media.example.com/{rendition.file.name}")
            self.assertEqual(list(image.get_privacy_controlled_file_urls()), expected_result)

    def test_invalid_privacy_value_raises_value_error(self):
        """Verify that invalid privacy values raise a ValueError."""
        with self.assertRaises(ValueError):
            ImageFactory(_privacy="invalid", collection=self.root_collection)

    @override_settings(
        STORAGES={"default": {"BACKEND": "cms.private_media.storages.ReliableAccessControlInMemoryStorage"}}
    )
    def test_file_permission_setting_success(self):
        """Test successful file permission setting using a storage backend that supports it."""
        with self.assertNoLogs("cms.private_media.bulk_operations"):
            private_image = ImageFactory(collection=self.root_collection)
            public_image = ImageFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection)

        self.assertFalse(private_image.has_outdated_file_permissions())
        self.assertFalse(public_image.has_outdated_file_permissions())

    @override_settings(
        STORAGES={"default": {"BACKEND": "cms.private_media.storages.FlakyAccessControlInMemoryStorage"}}
    )
    def test_file_permission_setting_failure(self):
        """Test graceful handling of file permission setting failures.

        Verifies that the system correctly tracks failed permission updates and
        maintains the outdated state when storage operations fail.
        """
        private_image = ImageFactory(collection=self.root_collection)
        public_image = ImageFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection)
        self.assertTrue(private_image.has_outdated_file_permissions())
        self.assertTrue(public_image.has_outdated_file_permissions())


@override_settings(
    WAGTAILFRONTENDCACHE={
        "default": {
            "BACKEND": "cms.private_media.tests.utils.MockFrontEndCacheBackend",
        },
    }
)
class TestPrivateImageManager(TestCase):
    model = get_image_model()

    @classmethod
    def setUpTestData(cls):
        cls.root_collection = Collection.objects.get(depth=1)

    def setUp(self):
        # Create six images with renditions (a mix of private and public)
        self.private_images = []
        self.public_images = []
        for _ in range(3):
            private_image = ImageFactory(collection=self.root_collection)
            public_image = ImageFactory(_privacy=Privacy.PUBLIC, collection=self.root_collection)
            private_image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20"))
            public_image.create_renditions(Filter("fill-10x10"), Filter("fill-20x20"))
            self.private_images.append(private_image)
            self.public_images.append(public_image)
        PURGED_URLS.clear()

    @override_settings(TASKS=TASKS_ENQUEUE_ON_COMMIT)
    def test_bulk_make_public(self):
        """Test the behaviour of PrivateImageManager.bulk_make_public()."""
        # Three image are already public, so only three should be updated
        qs = self.model.objects.all().prefetch_related("renditions")
        with self.assertNumQueries(4):
            # Query summary:
            # 1. to fetch the images
            # 2. to prefetch renditions
            # 3. to save updates
            # 4. to fetch sites to facilitate cache purging
            self.assertEqual(self.model.objects.bulk_make_public(qs), 3)

        # Serve URLs for private image renditions should have been purged as part of the update
        for obj in self.private_images:
            for rendition in obj.renditions.all():
                self.assertIn("http://localhost" + rendition.url, PURGED_URLS)

        # Verify all images are now public
        for obj in self.model.objects.only("_privacy", "file_permissions_last_set", "privacy_last_changed"):
            self.assertIs(obj.privacy, Privacy.PUBLIC)
            self.assertFalse(obj.has_outdated_file_permissions())

        # Another attempt should result in no updates
        with self.assertNumQueries(1):
            # Query summary:
            # 1. to fetch the images
            self.assertEqual(self.model.objects.bulk_make_public(self.model.objects.all()), 0)

    @override_settings(TASKS=TASKS_ENQUEUE_ON_COMMIT)
    def test_bulk_make_private(self):
        """Test the behaviour of PrivateImageManager.bulk_make_private()."""
        # Three images are already private, so only three should be updated
        qs = self.model.objects.all().prefetch_related("renditions")
        with self.assertNumQueries(4):
            # Query summary:
            # 1. to fetch the images
            # 2. to prefetch renditions
            # 3. to save updates
            # 4. to fetch sites to facilitate cache purging
            self.assertEqual(self.model.objects.bulk_make_private(qs), 3)

        # Serve URLs for public image renditions should have been purged as part of the update
        for obj in self.public_images:
            for rendition in obj.renditions.all():
                self.assertIn("http://localhost" + rendition.serve_url, PURGED_URLS)

        # Verify all images are now private
        for image in self.model.objects.only("_privacy", "file_permissions_last_set", "privacy_last_changed"):
            self.assertIs(image.privacy, Privacy.PRIVATE)
            self.assertFalse(image.has_outdated_file_permissions())

        # Another attempt should result in no updates
        with self.assertNumQueries(1):
            # Query summary:
            # 1. to fetch the images
            self.assertEqual(self.model.objects.bulk_make_private(self.model.objects.all()), 0)
