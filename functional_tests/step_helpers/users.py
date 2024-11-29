from functional_tests.step_helpers.factories import TEST_USER_PASSWORD, UserFactory


def create_cms_admin_user() -> tuple[str, str]:
    """Creates a CMS admin user using a factory, returns the username and password."""
    user = UserFactory()
    return user.username, TEST_USER_PASSWORD
