"""Dev-only helper: build a draft bundle of chart-bearing pages, ready to send for review by hand.

Sending the resulting bundle to preview exercises the synchronous chart render triggered by the
DRAFT -> IN_REVIEW transition (see BundleAdminForm._validate_charts_render_for_review).
"""

import json
import uuid
from argparse import ArgumentParser
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.urls import reverse

from cms.articles.models import ArticleSeriesPage
from cms.articles.tests.factories import StatisticalArticlePageFactory
from cms.bundles.enums import BundleStatus
from cms.bundles.models import Bundle, BundlePage


def chart_block(index: int) -> dict[str, Any]:
    """A line chart block with enough real data for the exporter to render something."""
    return {
        "type": "line_chart",
        "id": str(uuid.uuid4()),
        "value": {
            "figure_number": f"Figure {index}",
            "title": f"Test chart {index}",
            "subtitle": "Created by the create_chart_bundle command",
            "audio_description": f"A line chart showing made up data for test chart {index}.",
            "caption": "Office for National Statistics",
            "table": {
                "table_data": json.dumps(
                    {
                        "data": [
                            ["Period", "Series A", "Series B"],
                            ["2020", "100", "60"],
                            ["2021", "120", "72"],
                            ["2022", "115", "80"],
                            ["2023", "140", "95"],
                        ]
                    }
                )
            },
            "theme": "primary",
            "show_legend": True,
            "show_markers": False,
            "x_axis": {"title": ""},
            "y_axis": {"title": "Value"},
        },
    }


class Command(BaseCommand):
    help = "Create a draft bundle containing pages with chart blocks, to be sent for review manually."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--name", help="Bundle name. Defaults to a unique 'Chart test bundle <n>'.")
        parser.add_argument("--pages", type=int, default=1, help="Number of pages to create (default: 1).")
        parser.add_argument(
            "--charts-per-page", type=int, default=2, help="Number of chart blocks per page (default: 2)."
        )
        parser.add_argument(
            "--parent-id",
            type=int,
            help="ID of the ArticleSeriesPage to create the pages under. Defaults to the first one found.",
        )

    def get_parent(self, parent_id: int | None) -> ArticleSeriesPage:
        if parent_id:
            try:
                return ArticleSeriesPage.objects.get(pk=parent_id)
            except ArticleSeriesPage.DoesNotExist as exc:
                raise CommandError(f"No ArticleSeriesPage with id {parent_id}.") from exc

        if parent := ArticleSeriesPage.objects.first():
            return parent

        raise CommandError(
            "No ArticleSeriesPage found to create the pages under. Create an article series in the admin "
            "first, or pass --parent-id."
        )

    def get_user(self) -> Any:
        if user := get_user_model().objects.filter(is_superuser=True).order_by("pk").first():
            return user
        raise CommandError("No superuser found to own the bundle.")

    def get_bundle_name(self, name: str | None) -> str:
        if name:
            return name
        existing = Bundle.objects.filter(name__startswith="Chart test bundle").count()
        return f"Chart test bundle {existing + 1}"

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        parent = self.get_parent(options["parent_id"])
        user = self.get_user()

        bundle = Bundle.objects.create(
            name=self.get_bundle_name(options["name"]),
            created_by=user,
            status=BundleStatus.DRAFT,
        )

        for page_number in range(1, options["pages"] + 1):
            page = StatisticalArticlePageFactory(
                parent=parent,
                title=f"{bundle.name} - page {page_number}",
                live=False,
            )
            page.content = [
                {
                    "type": "section",
                    "id": str(uuid.uuid4()),
                    "value": {
                        "title": "Charts",
                        "content": [chart_block(i) for i in range(1, options["charts_per_page"] + 1)],
                    },
                }
            ]
            page.save()
            page.save_revision()

            BundlePage.objects.create(parent=bundle, page=page)
            self.stdout.write(f"Created page '{page.title}' with {options['charts_per_page']} chart(s)")

        edit_url = reverse("bundle:edit", args=[bundle.pk])
        self.stdout.write(
            self.style.SUCCESS(
                f"Created bundle '{bundle.name}' (id {bundle.pk}) with {options['pages']} page(s).\n"
                f"Send it for review at: http://localhost:8000{edit_url}"
            )
        )
