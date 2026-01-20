import argparse
import logging
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cms.teams.models import Team

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs teams from the identity API"
    identity_api_base_url: str | None = None
    service_auth_token: str | None = None

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run -- no changes will be made to the database.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options.get("dry_run", False)
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode. No changes will be made."))

        self.identity_api_base_url = getattr(settings, "IDENTITY_API_BASE_URL", None)
        if not self.identity_api_base_url:
            raise CommandError("IDENTITY_API_BASE_URL is not set in settings.")

        self.service_auth_token = getattr(settings, "SERVICE_AUTH_TOKEN", None)
        if not self.service_auth_token:
            raise CommandError("SERVICE_AUTH_TOKEN is not set in settings.")

        try:
            self.sync_teams(dry_run)
        except Exception as e:
            logger.exception("Team sync failed")
            raise CommandError(f"Team sync failed: {e}") from e

    def sync_teams(self, dry_run: bool) -> None:
        """Syncs teams from the identity API."""
        self.stdout.write("Syncing teams...")
        groups = self.fetch_groups_from_api()
        if groups is None:
            raise CommandError("Failed to fetch groups from the identity API.")

        self.update_teams(groups, dry_run=dry_run)

    def fetch_groups_from_api(self) -> list[dict] | None:
        """Fetches groups from the identity API."""
        url = f"{self.identity_api_base_url}/groups"
        try:
            return self._fetch_groups(url)
        except requests.RequestException:
            logger.exception("Failed to fetch groups from the API")
            return None

    def _fetch_groups(self, url: str) -> list[dict] | None:
        # Include both the standard Authorization header and the legacy X-Florence-Token.
        # The X-Florence-Token remains mandatory for now because some services still depend on older middleware.
        # Once all services are upgraded, we can remove the X-Florence-Token header entirely.
        headers = {
            "Authorization": f"Bearer {self.service_auth_token}",
            "X-Florence-Token": f"Bearer {self.service_auth_token}",
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        try:
            data: dict[str, Any] = response.json()
        except ValueError:
            logger.exception("Invalid JSON response from API")
            return None

        groups: list[dict] = data.get("groups", [])
        self.stdout.write(f"Fetched {len(groups)} groups from the API.")
        return groups

    @transaction.atomic
    def update_teams(self, groups: Iterable[dict], *, dry_run: bool) -> None:
        """Updates the local database with the teams fetched from the API."""
        # Fetch existing Teams from the database
        existing_teams: dict[str, Team] = {team.identifier: team for team in Team.objects.all()}
        active_team_ids = {team.identifier for team in existing_teams.values() if team.is_active}
        api_team_groups = [group for group in groups if group["id"] not in settings.ROLE_GROUP_IDS]
        teams_from_api: set[str] = {group["id"] for group in api_team_groups}

        for group in api_team_groups:
            self._update_team(group, existing_teams=existing_teams, dry_run=dry_run)

        # Deactivate teams not present in the API
        teams_to_deactivate = set(active_team_ids) - teams_from_api
        if teams_to_deactivate:
            self.stdout.write(f"Deactivating {len(teams_to_deactivate)} team(s) not present in the API.")
            for team_id in teams_to_deactivate:
                self.stdout.write(f"Deactivating team: {team_id} - {existing_teams[team_id].name}")

            if not dry_run:
                Team.objects.filter(identifier__in=teams_to_deactivate).update(is_active=False)

    def _update_team(self, group: Mapping, *, existing_teams: Mapping[str, Team], dry_run: bool) -> None:
        """Updates a single team in the database."""
        group_id: str = group["id"]
        name: str = group["name"].strip()
        precedence: int = group["precedence"]
        created_str: str = group["creation_date"]
        updated_str: str = group["last_modified_date"]

        created_at: datetime = datetime.fromisoformat(created_str).replace(tzinfo=UTC)
        updated_at: datetime = datetime.fromisoformat(updated_str).replace(tzinfo=UTC)

        if group_id in existing_teams:
            team = existing_teams[group_id]
            if (
                team.name != name
                or team.precedence != precedence
                or team.created_at != created_at
                or team.updated_at != updated_at
            ):
                self.stdout.write(f"Updating team: {group_id}")
                if not dry_run:
                    team.name = name
                    team.precedence = precedence
                    team.created_at = created_at
                    team.updated_at = updated_at
                    team.is_active = True
                    team.save()
        else:
            self.stdout.write(f"Creating new team: {name} (ID: {group_id})")
            if not dry_run:
                Team.objects.create(
                    identifier=group_id,
                    name=name,
                    precedence=precedence,
                    created_at=created_at,
                    updated_at=updated_at,
                    is_active=True,
                )
