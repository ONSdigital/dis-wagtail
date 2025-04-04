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

    def permission_check_helper(self, app: str, model: str, permission_type: str, has_permission: bool):
        """Helper method to check if a user has - or doesn't have - a permission for a model."""
        user_has_perm: bool = self.user.has_perm(f"{app}.{permission_type}_{model}")

        if has_permission:
            self.assertTrue(user_has_perm)
        else:
            self.assertFalse(user_has_perm)

    def all_permissions_check_helper(self, app: str, model: str, has_permission: bool):
        """Helper to check if the user has - or doesn't have - all permissions for a model."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.permission_check_helper(app, model, permission_type, has_permission)

    def page_permission_check_helper(self, permission_type: str, has_permission: bool):
        """Helper method to check if the group that the user is a member of
        has - or doesn't have - the given permission for the root page.
        """
        group = self.user.groups.first()
        root_page = Page.objects.get(depth=1)
        page_permission = Permission.objects.get(codename=f"{permission_type}_page")

        try:
            group_page_permissions = GroupPagePermission.objects.get(
                group=group,
                permission=page_permission,
                page=root_page,
            )
        except GroupPagePermission.DoesNotExist:
            group_page_permissions = None

        if has_permission:
            self.assertIsNotNone(group_page_permissions)
        else:
            self.assertIsNone(group_page_permissions)

    def collection_permission_check_helper(self, permission_type: str, collection_type: str, has_permission: bool):
        """Helper method to check if the group that the user is a member of
        has the given permission for a collection.
        """
        group = self.user.groups.first()
        root_collection = Collection.objects.get(depth=1)
        permission = Permission.objects.get(codename=f"{permission_type}_{collection_type}")

        try:
            group_collection_permission = GroupCollectionPermission.objects.get(
                group=group,
                permission=permission,
                collection=root_collection,
            )
        except GroupCollectionPermission.DoesNotExist:
            group_collection_permission = None

        if has_permission:
            self.assertIsNotNone(group_collection_permission)
        else:
            self.assertIsNone(group_collection_permission)

    def snippet_permission_check_helper(self, app: str, model: str, is_publishable: bool, has_permission: bool):
        """Helper method to check if the user has - or doesn't have - the permissions to manage a snippet."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.permission_check_helper(app, model, permission_type, has_permission)

        if is_publishable:
            self.permission_check_helper(app, model, "publish", has_permission)


class PublishingAdminPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.PUBLISHING_ADMINS_GROUP_NAME)

    def test_publishing_admin_can_access_admin(self):
        """Check that the Publishing Admin can access the Wagtail admin."""
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_publishing_admin_can_manage_pages(self):
        """Check that the Publishing Admin can manage the root page and its children."""
        for permission_type in WAGTAIL_PAGE_PERMISSION_TYPES:
            self.page_permission_check_helper(permission_type, has_permission=True)

    def test_publishing_admin_can_manage_images(self):
        """Check that the Publishing Admin can manage images."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "image", has_permission=True)

    def test_publishing_admin_can_choose_images(self):
        """Check that the Publishing Admin can choose images on pages."""
        self.collection_permission_check_helper("choose", "image", has_permission=True)

    def test_publishing_admin_can_manage_documents(self):
        """Check that the Publishing Admin can manage images."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "document", has_permission=True)

    def test_publishing_admin_can_choose_documents(self):
        """Check that the Publishing Admin can choose images on pages."""
        self.collection_permission_check_helper("choose", "document", has_permission=True)

    def test_publishing_admin_can_manage_glossary_term(self):
        """Check that the Publishing Admin can manage Glossary terms."""
        self.snippet_permission_check_helper("core", "glossaryterm", is_publishable=False, has_permission=True)

    def test_publishing_admin_can_manage_contact_details(self):
        """Check that the Publishing Admin can manage Contact details."""
        self.snippet_permission_check_helper("core", "contactdetails", is_publishable=False, has_permission=True)

    def test_publishing_admin_can_manage_main_menu(self):
        """Check that the Publishing Admin can manage and publish the main menu."""
        self.snippet_permission_check_helper("navigation", "mainmenu", is_publishable=True, has_permission=True)

    def test_publishing_admin_can_manage_footer_menu(self):
        """Check that the Publishing Admin can manage and publish the main menu."""
        self.snippet_permission_check_helper("navigation", "footermenu", is_publishable=True, has_permission=True)

    def test_publishing_admin_can_manage_bundles(self):
        self.all_permissions_check_helper("bundles", "bundle", has_permission=True)
        # also check that the PA can view bundles
        self.assertTrue(self.user.has_perm("bundles.view_bundle"))

    def test_publishing_admin_can_view_teams(self):
        self.assertTrue(self.user.has_perm("teams.view_team"))

    def test_publishing_admin_can_manage_redirects(self):
        self.all_permissions_check_helper("wagtailredirects", "redirect", has_permission=True)

    def test_publishing_admin_can_manage_navigation_settings(self):
        self.assertTrue(self.user.has_perm("navigation.change_navigationsettings"))

    def test_publishing_admin_can_manage_social_media_settings(self):
        self.assertTrue(self.user.has_perm("core.change_socialmediasettings"))

    def test_publishing_admin_log_entry(self):
        """Check that the Publishing Admin can see the logs."""
        self.assertTrue(self.user.has_perm("wagtailcore.view_logentry"))


class PublishingOfficerPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.PUBLISHING_OFFICERS_GROUP_NAME)

    def test_publishing_officer_can_access_admin(self):
        """Check that the Publishing Admin can access the Wagtail admin."""
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_publishing_officer_can_create_and_change_pages(self):
        """Check that the Publishing Officer can only add and change pages."""
        for permission_type in WAGTAIL_PAGE_PERMISSION_TYPES:
            if permission_type in ("add", "change"):
                self.page_permission_check_helper(permission_type, has_permission=True)
            else:
                # Publishing Officers should not have bulk_delete, lock, publish or unlock permissions
                self.page_permission_check_helper(permission_type, has_permission=False)

    def test_publishing_officer_cannot_manage_images(self):
        """Check that the Publishing Officer cannot manage image collection."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "image", has_permission=False)

    def test_publishing_officer_can_choose_images(self):
        """Check that the Publishing Officer can choose images on pages."""
        self.collection_permission_check_helper("choose", "image", has_permission=True)

    def test_publishing_officer_cannot_manage_documents(self):
        """Check that the Publishing Officer cannot manage document collection."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "collection", has_permission=False)

    def test_publishing_officer_can_choose_documents(self):
        """Check that the Publishing Officer can choose documents on pages."""
        self.collection_permission_check_helper("choose", "document", has_permission=True)

    def test_publishing_officer_cannot_manage_glossary_terms(self):
        """Check that the Publishing Officer can't manage Glossary terms."""
        self.snippet_permission_check_helper("core", "glossaryterm", is_publishable=False, has_permission=False)

    def test_publishing_officer_cannot_manage_contact_details(self):
        """Check that the Publishing Officer can't manage Contact details."""
        self.snippet_permission_check_helper("core", "contactdetails", is_publishable=False, has_permission=False)

    def test_publishing_officer_cannot_manage_main_menu(self):
        """Check that the Publishing Officer can't manage and publish the main menu."""
        self.snippet_permission_check_helper("navigation", "mainmenu", is_publishable=True, has_permission=False)

    def test_publishing_officer_cannot_manage_footer_menu(self):
        """Check that the Publishing Officer can't manage and publish the main menu."""
        self.snippet_permission_check_helper("navigation", "footermenu", is_publishable=True, has_permission=False)

    def test_publishing_officer_can_manage_bundles(self):
        """Check that the Publishing Officer can manage bundles."""
        self.all_permissions_check_helper("bundles", "bundle", has_permission=True)
        # also check that the PO can view bundles
        self.assertTrue(self.user.has_perm("bundles.view_bundle"))

    def test_publishing_officer_can_view_teams(self):
        """Check that the Publishing Officer can view teams."""
        self.assertTrue(self.user.has_perm("teams.view_team"))

    def test_publishing_officer_cannot_manage_redirects(self):
        """Check that the Publishing Officer can't manage redirects."""
        self.all_permissions_check_helper("wagtailredirects", "redirect", has_permission=False)

    def test_publishing_officer_cannot_manage_navigation_settings(self):
        """Check that the Publishing Officer can't change navigation settings."""
        self.assertFalse(self.user.has_perm("navigation.change_navigationsettings"))

    def test_publishing_officer_cannot_manage_social_media_settings(self):
        """Check that the Publishing Officer can't change social media settings."""
        self.assertFalse(self.user.has_perm("core.change_socialmediasettings"))

    def test_publishing_officer_log_entry(self):
        """Check that the Publishing Officer can't see the logs."""
        self.assertFalse(self.user.has_perm("wagtailcore.view_logentry"))


class ViewerPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.VIEWERS_GROUP_NAME)

    def test_viewers_can_access_admin(self):
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_viewer_doesnt_have_page_permissions(self):
        """Check that the Viewer doesn't have any permissions for pages."""
        for permission_type in WAGTAIL_PAGE_PERMISSION_TYPES:
            self.page_permission_check_helper(permission_type, has_permission=False)

    def test_viewer_cannot_manage_images(self):
        """Check that the Viewer can't manage image collection."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "image", has_permission=False)

    def test_viewer_cannot_choose_images(self):
        """Check that the Viewer can't choose images on pages."""
        self.collection_permission_check_helper("choose", "image", has_permission=False)

    def test_viewer_cannot_manage_documents(self):
        """Check that the Viewer can't manage document collection."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            self.collection_permission_check_helper(permission_type, "collection", has_permission=False)

    def test_viewer_cannot_choose_documents(self):
        """Check that the Viewer can't choose documents on pages."""
        self.collection_permission_check_helper("choose", "document", has_permission=False)

    def test_viewer_cannot_manage_glossary_terms(self):
        """Check that the Viewer can't manage Glossary terms."""
        self.snippet_permission_check_helper("core", "glossaryterm", is_publishable=False, has_permission=False)

    def test_viewer_cannot_manage_contact_details(self):
        """Check that the Viewer can't manage Contact details."""
        self.snippet_permission_check_helper("core", "contactdetails", is_publishable=False, has_permission=False)

    def test_viewer_cannot_manage_main_menu(self):
        """Check that the Viewer can't manage and publish the main menu."""
        self.snippet_permission_check_helper("navigation", "mainmenu", is_publishable=True, has_permission=False)

    def test_viewer_cannot_manage_footer_menu(self):
        """Check that the Viewer can't manage and publish the main menu."""
        self.snippet_permission_check_helper("navigation", "footermenu", is_publishable=True, has_permission=False)

    def test_viewer_can_view_bundles(self):
        """Check that the Viewer can only view bundles and not manage it."""
        self.all_permissions_check_helper("bundles", "bundle", has_permission=False)

        self.assertTrue(self.user.has_perm("bundles.view_bundle"))

    def test_viewer_cannot_view_teams(self):
        """Check that the Viewer can't view teams."""
        self.assertFalse(self.user.has_perm("teams.view_team"))

    def test_viewer_cannot_manage_redirects(self):
        """Check that the Viewer can't manage redirects."""
        self.all_permissions_check_helper("wagtailredirects", "redirect", has_permission=False)

    def test_viewer_cannot_manage_navigation_settings(self):
        """Check that the Viewer can't change navigation settings."""
        self.assertFalse(self.user.has_perm("navigation.change_navigationsettings"))

    def test_viewer_cannot_manage_social_media_settings(self):
        """Check that the Viewer can't change social media settings."""
        self.assertFalse(self.user.has_perm("core.change_socialmediasettings"))

    def test_viewer_cannot_see_reporting(self):
        """Check that the Viewer can't see the logs."""
        self.assertFalse(self.user.has_perm("wagtailcore.view_logentry"))
