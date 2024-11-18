from django.contrib.auth.hashers import make_password
from factory.django import DjangoModelFactory

DEFAULT_TEST_PASSWORD = "default_test_password"  # pragma: allowlist secret # noqa: S105


class UserFactory(DjangoModelFactory):
    """User factory for testing."""

    class Meta:
        model = "users.User"

    username = "test_user"
    password = make_password(DEFAULT_TEST_PASSWORD)
    is_active = True
    is_staff = True
    is_superuser = True  # This is currently required to log into admin site
