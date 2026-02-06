from django.conf import settings
from django.contrib.auth.models import Group

from cms.users.tests.factories import UserFactory


def get_user_data(user) -> dict[str, str]:
    return {
        "user": user,
        "username": user.username,
        "full_name": f"{user.first_name} {user.last_name}",
        "password": "password",  # pragma: allowlist secret
    }


def create_user(user_type: str) -> dict[str, str]:
    match user_type:
        case "Publishing Admin":
            user = UserFactory()
            user.groups.add(Group.objects.get(name=settings.PUBLISHING_ADMINS_GROUP_NAME))
        case "Publishing Officer":
            user = UserFactory()
            user.groups.add(Group.objects.get(name=settings.PUBLISHING_OFFICERS_GROUP_NAME))
        case "Viewer":
            user = UserFactory()
            user.groups.add(Group.objects.get(name=settings.VIEWERS_GROUP_NAME))
        case _:
            user = UserFactory(is_superuser=True)

    return get_user_data(user)
