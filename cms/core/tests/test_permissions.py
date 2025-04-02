from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from wagtail.models import Collection, GroupCollectionPermission, GroupPagePermission, Page

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

    def page_permission_check_helper(self, permission_type: str):
        """Helper method to check if the group that the user is a member of
        has the given permission for the root page.
        """
        group = self.user.groups.first()
        root_page = Page.objects.get(depth=1)
        page_permission = Permission.objects.get(codename=f"{permission_type}_page")

        group_page_permissions = GroupPagePermission.objects.get(
            group=group,
            permission=page_permission,
            page=root_page,
        )

        self.assertIsNotNone(group_page_permissions)

    def collection_permission_check_helper(self, permission_type: str, collection_type: str):
        """Helper method to check if the group that the user is a member of
        has the given permission for a collection.
        """
        group = self.user.groups.first()
        root_collection = Collection.objects.get(depth=1)
        permission = Permission.objects.get(codename=f"{permission_type}_{collection_type}")

        group_page_permissions = GroupCollectionPermission.objects.get(
            group=group,
            permission=permission,
            collection=root_collection,
        )

        self.assertIsNotNone(group_page_permissions)


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
            self.page_permission_check_helper(permission_type)

    def test_publishing_admin_can_manage_images(self):
        """Check that the Publishing Admin can manage images."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "image")

    def test_publishing_admin_can_choose_images(self):
        """Check that the Publishing Admin can choose images on pages."""
        self.collection_permission_check_helper("choose", "image")

    def test_publishing_admin_can_manage_documents(self):
        """Check that the Publishing Admin can manage images."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "document")

    def test_publishing_admin_can_choose_documents(self):
        """Check that the Publishing Admin can choose images on pages."""
        self.collection_permission_check_helper("choose", "document")

    def test_publishing_admin_can_manage_glossary_term(self):
        self.all_permissions_check_helper("core", "glossaryterm")

    def test_publishing_admin_can_manage_contact_details(self):
        self.all_permissions_check_helper("core", "contactdetails")

    def test_publishing_admin_can_manage_main_menu(self):
        self.all_permissions_check_helper("navigation", "mainmenu")
        # also check that the PA can publish the main menu
        self.assertTrue(self.user.has_perm("navigation.publish_mainmenu"))

    def test_publishing_admin_can_manage_footer_menu(self):
        self.all_permissions_check_helper("navigation", "footermenu")
        # also check that the PA can publish the footer menu
        self.assertTrue(self.user.has_perm("navigation.publish_footermenu"))

    def test_publishing_admin_can_manage_bundles(self):
        self.all_permissions_check_helper("bundles", "bundle")
        # also check that the PA can view bundles
        self.assertTrue(self.user.has_perm("bundles.view_bundle"))

    def test_publishing_admin_can_view_teams(self):
        self.assertTrue(self.user.has_perm("teams.view_team"))

    def test_publishing_admin_can_manage_redirects(self):
        self.all_permissions_check_helper("wagtailredirects", "redirect")

    def test_publishing_admin_can_manage_navigation_settings(self):
        self.assertTrue(self.user.has_perm("navigation.change_navigationsettings"))

    def test_publishing_admin_can_manage_social_media_settings(self):
        self.assertTrue(self.user.has_perm("core.change_socialmediasettings"))


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
        # also check that the PO can view bundles
        self.assertTrue(self.user.has_perm("bundles.view_bundle"))

    def test_publishing_officer_can_manage_pages(self):
        """Check that the Publishing Officer can create and edit the root page and its children."""
        for permission_type in ("add", "change"):
            self.page_permission_check_helper(permission_type)

    def test_publishing_officer_can_choose_images(self):
        """Check that the Publishing Officer can choose images on pages."""
        self.collection_permission_check_helper("choose", "image")

    def test_publishing_officer_can_choose_documents(self):
        """Check that the Publishing Officer can choose documents on pages."""
        self.collection_permission_check_helper("choose", "document")

    def test_publishing_officer_can_view_teams(self):
        self.assertTrue(self.user.has_perm("teams.view_team"))


class ViewerPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.VIEWERS_GROUP_NAME)

    def test_viewers_can_access_admin(self):
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_viewers_can_view_bundles(self):
        self.assertTrue(self.user.has_perm("bundles.view_bundle"))
