import factory
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission
from factory.django import DjangoModelFactory

from cms.users.models import User


class GroupFactory(DjangoModelFactory):
    class Meta:
        model = Group
        django_get_or_create = ("name",)

    @factory.post_generation
    def access_admin(self, create, extracted, **kwargs):
        """Creates BundlePage instances for the bundle.

        Usage:
            # Create a Django generic_user group
            group = GroupFactory()

            # Create a Django generic_user group with Wagtail admin access
            group = GroupFactory(access_admin=True)
        """
        if not create:
            return

        if extracted:
            admin_permission = Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin")
            self.permissions.add(admin_permission)


class UserFactory(DjangoModelFactory):
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    password = factory.LazyFunction(lambda: make_password("password"))
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    class Meta:
        model = User

    @factory.post_generation
    def access_admin(self, create, extracted, **kwargs):
        """Creates BundlePage instances for the bundle.

        Usage:
            # Create a Django generic_user group
            generic_user = UserFactory()

            # Create a Django generic_user group with Wagtail admin access
            generic_user = UserFactory(access_admin=True)
        """
        if not create:
            return

        if extracted:
            admin_permission = Permission.objects.get(content_type__app_label="wagtailadmin", codename="access_admin")
            self.user_permissions.add(admin_permission)
