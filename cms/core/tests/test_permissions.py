from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase

from cms.users.tests.factories import UserFactory

WAGTAIL_PERMISSION_TYPES = ["add", "change", "delete"]

WAGTAIL_PAGE_PERMISSION_TYPES = ["add", "change", "bulk_delete", "lock", "publish", "unlock"]


class PermissionsTestCase(TestCase):
    @classmethod
    def create_user(cls, group_name):
        """Helper method to create a user and assign them to a group."""
        cls.user = UserFactory()

        group = Group.objects.get(name=group_name)
        group.user_set.add(cls.user)

    def all_permissions_check_helper(self, app: str, model: str):
        """Helper method to check if a user has all permissions for a model."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.assertTrue(self.user.has_perm(f"{app}.{permission_type}_{model}"))


class PublishingAdminPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.PUBLISHING_ADMINS_GROUP_NAME)

    def test_publishing_admin_can_access_admin(self):
        """Check that the Publishing Admin can access the Wagtail admin."""
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_publishing_admin_log_entry(self):
        """Check that the Publishing Admin can see the logs."""
        self.assertTrue(self.user.has_perm("wagtailcore.view_logentry"))

    def test_publishing_admin_can_manage_pages(self):
        """Check that the Publishing Admin can manage the root page and its children."""
        for permission_type in WAGTAIL_PAGE_PERMISSION_TYPES:
            self.assertTrue(self.user.has_perm(f"wagtailcore.{permission_type}_page"))

    def test_publishing_admin_can_manage_images(self):
        """Check that the Publishing Admin can manage images."""
        self.all_permissions_check_helper("wagtailimages", "image")

    def test_publishing_admin_can_manage_glossary_term(self):
        self.all_permissions_check_helper("core", "glossaryterm")

    def test_publishing_admin_can_manage_contact_details(self):
        self.all_permissions_check_helper("core", "contactdetails")

    def test_publishing_admin_can_manage_main_menu(self):
        self.all_permissions_check_helper("navigation", "mainmenu")

    def test_publishing_admin_can_manage_footer_menu(self):
        self.all_permissions_check_helper("navigation", "footermenu")

    def test_publishing_admin_can_manage_bundles(self):
        """Check that the Publishing Admin can manage bundles."""
        self.all_permissions_check_helper("bundles", "bundle")


class PublishingOfficerPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.PUBLISHING_OFFICERS_GROUP_NAME)

    def test_publishing_officer_can_access_admin(self):
        """Check that the Publishing Admin can access the Wagtail admin."""
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_publishing_officer_can_manage_bundle(self):
        """Check that the Publishing Officer can manage bundles."""
        self.all_permissions_check_helper("bundles", "bundle")

    def test_publishing_officer_can_manage_pages(self):
        """Check that the Publishing Officer can create and edit the root page and its children."""
        for permission_type in ("add", "change"):
            self.assertTrue(self.user.has_perm(f"wagtailcore.{permission_type}_page"))

    def test_publishing_officer_can_choose_image(self):
        """Check that the Publishing Officer can choose an images on pages."""
        self.assertTrue(self.user.has_perm("wagtailimages.choose_image"))


class ViewerPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.VIEWERS_GROUP_NAME)

    def test_viewers_can_access_admin(self):
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_viewers_can_view_bundles(self):
        self.assertTrue(self.user.has_perm("bundles.view_bundle"))
