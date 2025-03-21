from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase

from cms.users.models import User


class PermissionsTestCase(TestCase): ...


WAGTAIL_PERMISSION_PREFIXES = [
    "add_",
    "change_",
    "delete_",
    "view_",
]

# Taken from:
# https://github.com/wagtail/wagtail/blob/8f640a8cdb0dfcf14e611d33cbff388d5db7cf9d/wagtail/models/pages.py#L264
WAGTAIL_PAGE_PERMISSION_TYPES = [
    "add",
    "bulk_delete",
    "change",
    "lock",
    "publish",
    "unlock",
]


class PublishingAdminPermissionsTestCase(PermissionsTestCase):
    @classmethod
    def setUpTestData(cls):
        # Create user
        cls.user = User(first_name="Publishing", last_name="Officer")
        cls.user.save()

        # Assign user to group
        group = Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME)
        group.user_set.add(cls.user)
        group.save()

    def test_publishing_admin_can_access_admin(self):
        self.assertTrue(self.user.has_perm("wagtailadmin.access_admin"))

    def test_publishing_admin_log_entry(self):
        self.assertTrue(self.user.has_perm("wagtailcore.view_logentry"))

    def test_publishing_admin_can_manage_home_page(self):
        app = "home"
        model = "homepage"

        for permission_type in WAGTAIL_PAGE_PERMISSION_TYPES:
            self.assertTrue(self.user.has_perm(f"{app}.{permission_type}_{model}"))

    def test_publishing_admin_can_add_highlighted_articles_on_topic_page(self):
        self.assertTrue(self.user.has_perm("wagtailadmin.add_topic_page_highlighted_articles"))

    def test_publishing_admin_can_manage_glossary_term(self):
        for permission_prefix in WAGTAIL_PERMISSION_PREFIXES:
            self.assertTrue(self.user.has_perm(f"core.{permission_prefix}glossaryterm"))

    def test_publishing_admin_can_manage_contact_details(self):
        for permission_prefix in WAGTAIL_PERMISSION_PREFIXES:
            self.assertTrue(self.user.has_perm(f"core.{permission_prefix}contactdetails"))

    def test_publishing_admin_can_manage_main_menu(self):
        for permission_prefix in WAGTAIL_PERMISSION_PREFIXES:
            self.assertTrue(self.user.has_perm(f"navigation.{permission_prefix}mainmenu"))

    def test_publishing_admin_can_manage_footer_menu(self):
        for permission_prefix in WAGTAIL_PERMISSION_PREFIXES:
            self.assertTrue(self.user.has_perm(f"navigation.{permission_prefix}footermenu"))

    def test_publishing_admin_can_add_bundle(self):
        for permission_prefix in WAGTAIL_PERMISSION_PREFIXES:
            self.assertTrue(self.user.has_perm(f"bundles.{permission_prefix}bundle"))


class PublishingOfficerPermissionsTestCase(PermissionsTestCase): ...


class ViewerPermissionsTestCase(PermissionsTestCase): ...
