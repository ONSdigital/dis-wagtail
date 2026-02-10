import http
import importlib

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Collection, GroupCollectionPermission, GroupPagePermission, Page

from cms.core.models.snippets import ContactDetails
from cms.users.tests.factories import UserFactory

assign_permission_to_group = importlib.import_module(
    "cms.core.migrations.0006_update_user_groups"
).assign_permission_to_group


WAGTAIL_PERMISSION_TYPES = ["add", "change", "delete"]

WAGTAIL_PAGE_PERMISSION_TYPES = ["add", "change", "bulk_delete", "lock", "publish", "unlock"]


class TestPermissions(TestCase):
    """Test edge cases for the mechanism used for adding permissions in the data migration."""

    def test_raises_exception_when_app_not_found(self):
        """Check that an exception is raised when an app isn't registered."""
        app = "non_existent_app"
        model = "contactdetails"

        permission_codename = "add_contactdetails"
        group_name = settings.PUBLISHING_ADMINS_GROUP_NAME

        with self.assertRaises(LookupError):
            assign_permission_to_group(apps, group_name, permission_codename, app, model)

    def test_raises_exception_when_model_not_found(self):
        """Check that an exception is raised when a model isn't registered in an app."""
        app = "core"
        model = "non_existent_model"
        permission_codename = "add_contactdetails"
        group_name = settings.PUBLISHING_ADMINS_GROUP_NAME

        with self.assertRaises(LookupError):
            assign_permission_to_group(apps, group_name, permission_codename, app, model)

    def test_raises_exception_when_group_not_found(self):
        """Check that an exception is raised when a group doesn't exist."""
        app = "core"
        model = "contactdetails"
        permission_codename = "add_contactdetails"
        group_name = "non_existent_group"

        with self.assertRaises(Group.DoesNotExist):
            assign_permission_to_group(apps, group_name, permission_codename, app, model)

    def test_user_can_add_model_with_permission(self):
        """Check that the user can add a Contact Details snippet when they have the required permission."""
        # the Publishing Admin group has the core.add_contactdetails permission
        group_name = settings.PUBLISHING_ADMINS_GROUP_NAME

        user = UserFactory()
        group = Group.objects.get(name=group_name)
        group.user_set.add(user)

        self.client.force_login(user)

        add_url = reverse("wagtailsnippets_core_contactdetails:add")

        post_data = {
            "name": "Contact details",
            "email": "example@mail.com",
            "phone": "1233456789",
        }

        response = self.client.post(add_url, post_data)

        self.assertTrue(user.has_perm("core.add_contactdetails"))

        self.assertEqual(
            response.status_code,
            http.HTTPStatus.FOUND,
        )

        contact_details = ContactDetails.objects.get(name="Contact details")
        self.assertIsNotNone(contact_details)

    def test_user_cannot_add_model_without_permission(self):
        """Check that the user cannot add a Contact Details snippet when they don't have the required permission."""
        # the Viewer group doesn't have the core.add_contactdetails permission
        group_name = settings.VIEWERS_GROUP_NAME

        user = UserFactory()
        group = Group.objects.get(name=group_name)
        group.user_set.add(user)

        self.client.force_login(user)

        add_url = reverse("wagtailsnippets_core_contactdetails:add")
        post_data = {
            "name": "Contact details",
            "email": "example@mail.com",
            "phone": "1233456789",
        }

        response = self.client.post(add_url, post_data, follow=True)

        self.assertFalse(user.has_perm("core.add_contactdetails"))

        self.assertEqual(
            response.status_code,
            http.HTTPStatus.OK,
        )
        self.assertIn(
            "Sorry, you do not have permission to access this area.", response.content.decode(encoding="utf-8")
        )

        with self.assertRaises(ContactDetails.DoesNotExist):
            contact_details = ContactDetails.objects.get(name="Contact details")
            self.assertIsNone(contact_details)


class BaseGroupPermissionTestCase(TestCase):
    """Base class for all group permission test cases."""

    @classmethod
    def create_user(cls, group_name):
        """Helper method to create a user and assign them to a group."""
        cls.user = UserFactory()

        group = Group.objects.get(name=group_name)
        group.user_set.add(cls.user)

        cls.user_permissions = list(cls.user.user_permissions.all() | Permission.objects.filter(group__user=cls.user))

    def check_and_remove_from_user_permissions_helper(self, app: str, model: str, permission_type: str) -> None:
        """Assert the user has the permission and if so remove it from the temporary user permission list."""
        permission_str = f"{app}.{permission_type}_{model}" if model else f"{app}.{permission_type}"
        codename = f"{permission_type}_{model}" if model else permission_type
        self.assertTrue(self.user.has_perm(permission_str))
        permission = Permission.objects.get(content_type__app_label=app, codename=codename)
        self.user_permissions.remove(permission)
        self.assertNotIn(permission, self.user_permissions)

    def snippet_permission_check_helper(self, app: str, model: str, is_publishable: bool, expected_has_perm: bool):
        """Helper method to check if the user has - or doesn't have - the permissions to manage a snippet."""
        for permission_type in WAGTAIL_PERMISSION_TYPES:
            actual_has_perm: bool = self.user.has_perm(f"{app}.{permission_type}_{model}")
            self.assertEqual(expected_has_perm, actual_has_perm)

        if is_publishable:
            actual_has_perm: bool = self.user.has_perm(f"{app}.publish_{model}")
            self.assertEqual(expected_has_perm, actual_has_perm)

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


class PublishingAdminPermissionsTestCase(BaseGroupPermissionTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.PUBLISHING_ADMINS_GROUP_NAME)

    def test_publishing_admin_permissions(self):
        """Check that the Publishing Admin has all required permissions and not more."""
        self.check_and_remove_from_user_permissions_helper("wagtailadmin", "admin", "access")

        self.check_and_remove_from_user_permissions_helper("teams", "team", "view")

        default_permissions_plus_publish = [*WAGTAIL_PERMISSION_TYPES, "publish"]
        # Snippet permissions (app, model, permission types)
        snippet_permissions = [
            ("core", "definition", default_permissions_plus_publish),
            ("core", "contactdetails", default_permissions_plus_publish),
            ("navigation", "mainmenu", default_permissions_plus_publish),
            ("navigation", "footermenu", default_permissions_plus_publish),
        ]

        for app, model, permission_types in snippet_permissions:
            for permission_type in permission_types:
                self.check_and_remove_from_user_permissions_helper(app, model, permission_type)

        for permission_type in [*WAGTAIL_PERMISSION_TYPES, "view"]:
            self.check_and_remove_from_user_permissions_helper("bundles", "bundle", permission_type)

        self.check_and_remove_from_user_permissions_helper("core", "socialmediasettings", "change")
        self.check_and_remove_from_user_permissions_helper("wagtailcore", "logentry", "view")

        self.check_and_remove_from_user_permissions_helper("release_calendar", "notice", "modify")

        self.check_and_remove_from_user_permissions_helper("datasets", "datasets", "access_unpublished")

        self.check_and_remove_from_user_permissions_helper("wagtailadmin", "", "unlock_workflow_tasks")

        self.check_and_remove_from_user_permissions_helper(
            "simple_translation", "simpletranslation", "submit_translation"
        )

        # Publishing Admins should not have change_navigationsettings permission
        self.assertFalse(self.user.has_perm("navigation.change_navigationsettings"))

        # Check that there are no other unexpected permissions
        self.assertListEqual([], self.user_permissions)

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

    def test_publishing_admin_cannot_manage_redirects(self):
        """Check that the Publishing Admin does not have permissions to manage wagtailredirects.redirect."""
        self.snippet_permission_check_helper(
            "wagtailredirects", "redirect", is_publishable=False, expected_has_perm=False
        )


class PublishingOfficerPermissionsTestCase(BaseGroupPermissionTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.PUBLISHING_OFFICERS_GROUP_NAME)

    def test_publishing_officer_permissions(self):
        """Check that the Publishing Officer has all required permissions but not more."""
        self.check_and_remove_from_user_permissions_helper("wagtailadmin", "admin", "access")

        for permission_type in [*WAGTAIL_PERMISSION_TYPES, "view"]:
            self.check_and_remove_from_user_permissions_helper("bundles", "bundle", permission_type)

        self.check_and_remove_from_user_permissions_helper("teams", "team", "view")

        self.check_and_remove_from_user_permissions_helper("datasets", "datasets", "access_unpublished")

        # Publishing Officers should not have change_navigationsettings permission
        self.assertFalse(self.user.has_perm("navigation.change_navigationsettings"))

        # Publishing Officers should not have submit_translation permission
        self.assertFalse(self.user.has_perm("simple_translation.submit_translation"))

        # Check that there are no other unexpected permissions
        self.assertListEqual([], self.user_permissions)

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

    def test_publishing_officer_cannot_manage_redirects(self):
        """Check that the Publishing Officer does not have permissions to manage wagtailredirects.redirect."""
        self.snippet_permission_check_helper(
            "wagtailredirects", "redirect", is_publishable=False, expected_has_perm=False
        )


class ViewerPermissionsTestCase(BaseGroupPermissionTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_user(group_name=settings.VIEWERS_GROUP_NAME)

    def test_viewer_permissions(self):
        """Check that the Viewer has all required permissions and not more."""
        self.check_and_remove_from_user_permissions_helper("wagtailadmin", "admin", "access")

        self.check_and_remove_from_user_permissions_helper("bundles", "bundle", "view")

        # Viewers should not have change_navigationsettings permission
        self.assertFalse(self.user.has_perm("navigation.change_navigationsettings"))

        # Viewers should not have submit_translation permission
        self.assertFalse(self.user.has_perm("simple_translation.submit_translation"))

        # Check that there are no other unexpected permissions
        self.assertListEqual([], self.user_permissions)

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

    def test_viewer_cannot_manage_redirects(self):
        """Check that the Viewer does not have permissions to manage wagtailredirects.redirect."""
        self.snippet_permission_check_helper(
            "wagtailredirects", "redirect", is_publishable=False, expected_has_perm=False
        )


class SuperuserPermissionsTestCase(BaseGroupPermissionTestCase):
    def setUp(self):
        self.user = UserFactory(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)

    def test_superuser_can_manage_redirects(self):
        """Check that the superuser has permissions to manage wagtailredirects.redirect."""
        self.snippet_permission_check_helper(
            "wagtailredirects", "redirect", is_publishable=False, expected_has_perm=True
        )
