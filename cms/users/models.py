from collections.abc import Iterable

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.functional import cached_property

from cms.teams.models import Team


class User(AbstractUser):
    """Barebones custom user model."""

    # Unique identifier for user lookup, as emails (used as usernames) may change.
    external_user_id = models.UUIDField(unique=True, null=True, editable=False)
    teams = models.ManyToManyField("teams.Team", related_name="users", blank=True)

    @property
    def is_external_user(self) -> bool:
        """Return True for users who originate from an external identity provider
        (i.e. they have an external_user_id) and have no usable password set.
        External accounts rely on third-party authentication, so they should
        never possess a native password.
        """
        return self.external_user_id is not None and not self.has_usable_password()

    def assign_groups_and_teams(self, /, groups_ids: Iterable[str]) -> None:
        """Assign groups and teams to the user based on their Cognito groups."""
        self._assign_groups(groups_ids)
        self._assign_teams(groups_ids)

    @cached_property
    def active_team_ids(self) -> list[int]:
        return list(self.teams.filter(is_active=True).values_list("pk", flat=True))

    def _assign_groups(self, /, groups_ids: Iterable[str]) -> None:
        """Assign groups to the user based on their Cognito groups."""
        role_to_group = {
            "role-admin": settings.PUBLISHING_ADMINS_GROUP_NAME,
            "role-publisher": settings.PUBLISHING_OFFICERS_GROUP_NAME,
        }

        groups = {name: Group.objects.get(name=group_name) for name, group_name in role_to_group.items()}
        viewer_group = Group.objects.get(name=settings.VIEWERS_GROUP_NAME)

        # Assign or remove groups based on roles
        for role, group in groups.items():
            if role in groups_ids:
                self.groups.add(group)
            else:
                self.groups.remove(group)

        # Always add the viewer group
        self.groups.add(viewer_group)

    def _assign_teams(self, /, groups_ids: Iterable[str]) -> None:
        """Assign teams to the user based on their Cognito groups."""
        teams_to_add = set(groups_ids) - set(settings.ROLE_GROUP_IDS)
        existing_teams = {team.identifier: team for team in Team.objects.filter(identifier__in=teams_to_add)}
        missing_team_ids = teams_to_add - set(existing_teams.keys())

        # Create missing teams in bulk
        if missing_team_ids:
            missing_teams = [
                Team(
                    identifier=team_id,
                    name=team_id.replace("-", " ").title(),  # Temporary name, will be updated on sync
                )
                for team_id in missing_team_ids
            ]
            Team.objects.bulk_create(missing_teams)
            # Refresh the queryset to include newly created teams
            new_teams = Team.objects.filter(identifier__in=missing_team_ids)
            existing_teams |= {team.identifier: team for team in new_teams}

        teams_for_user = list(existing_teams.values())
        self.teams.set(teams_for_user)

    def update_details(self, *, email: str, first_name: str, last_name: str, created: bool) -> None:
        """Update user details regardless of whether the user was created or not as the fields may change.
        If created, set an unusable password for the user.
        """
        self.username = email
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        if created:
            self.set_unusable_password()
