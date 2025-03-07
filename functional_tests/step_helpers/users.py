from cms.users.tests.factories import UserFactory


def create_cms_admin_user() -> tuple[str, str, str]:
    """Creates a CMS admin user using a factory, returns the username and password."""
    user = UserFactory(is_superuser=True)
    return user.username, f"{user.first_name} {user.last_name}", "password"
