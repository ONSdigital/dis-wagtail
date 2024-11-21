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

# Role Groups
ROLE_GROUP_IDS: set[str] = {"role-admin", "role-publisher"}


class Command(BaseCommand):
    help = "Syncs teams from the identity API"
    identity_api_url: str | None = None

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

        self.identity_api_url = getattr(settings, "IDENTITY_API_URL", None)
        if not self.identity_api_url:
            raise CommandError("IDENTITY_API_URL is not set in settings.")

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
        url = f"{self.identity_api_url}/groups"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            groups: list[dict] = data.get("groups", [])
            self.stdout.write(f"Fetched {len(groups)} groups from the API.")
            return groups
        except requests.RequestException as e:
            logger.error("Error fetching groups from API: %s", e)
            return None

    @transaction.atomic
    def update_teams(self, groups: Iterable[dict], *, dry_run: bool) -> None:
        """Updates the local database with the teams fetched from the API."""
        # Fetch existing Teams from the database
        existing_teams: dict[str, Team] = {team.identifier: team for team in Team.objects.all()}
        teams_from_api: set[str] = {group["id"] for group in groups if group["id"] not in ROLE_GROUP_IDS}

        for group in groups:
            self._update_team(group, existing_teams=existing_teams, dry_run=dry_run)

        # Deactivate teams not present in the API
        teams_to_deactivate = existing_teams.keys() - teams_from_api
        if teams_to_deactivate:
            self.stdout.write(f"Deactivating {len(teams_to_deactivate)} team(s) not present in the API.")

            for team_id in teams_to_deactivate:
                team = existing_teams[team_id]
                self.stdout.write(f"Deactivating team: {team_id} - {team.name}")

            if not dry_run:
                Team.objects.filter(identifier__in=teams_to_deactivate).update(is_active=False)

    def _update_team(self, group: Mapping, *, existing_teams: Mapping[str, Team], dry_run: bool) -> None:
        """Updates a single team in the database."""
        group_id: str = group["id"]

        if group_id in ROLE_GROUP_IDS:
            # Skip role groups as they are handled separately
            return

        name: str = group["name"].strip()
        precedence: int = group["precedence"]
        created_str: str = group["created"]

        # Parse the created date string to a datetime object
        created_at: datetime = datetime.fromisoformat(created_str).replace(tzinfo=UTC)

        if group_id in existing_teams:
            team = existing_teams[group_id]

            if team.name != name or team.precedence != precedence or team.created_at != created_at:
                self.stdout.write(f"Updating team: {group_id}")
                if not dry_run:
                    team.name = name
                    team.precedence = precedence
                    team.created_at = created_at
                    team.save()
        else:
            self.stdout.write(f"Creating new team: {name} (ID: {group_id})")
            if not dry_run:
                Team.objects.create(
                    identifier=group_id,
                    name=name,
                    precedence=precedence,
                    created_at=created_at,
                    is_active=True,
                )
