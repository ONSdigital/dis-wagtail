from cms.users.tests.factories import UserFactory


def create_cms_admin_user() -> dict[str, str]:
    """Creates a CMS admin user using a factory, returns the username and password."""
    user = UserFactory(is_superuser=True)
    return {
        "username": user.username,
        "full_name": f"{user.first_name} {user.last_name}",
        "password": "password",  # pragma: allowlist secret
    }
