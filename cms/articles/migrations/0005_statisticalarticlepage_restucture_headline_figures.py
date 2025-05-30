# Generated by Django 5.1.8 on 2025-05-06 10:17

import json
import uuid

from django.db import migrations


def denest_headline_figures(headline_figures):
    figures = headline_figures[0]["value"].copy()
    # If figures not a list, return it
    if not isinstance(figures, list):
        return figures
    for figure in figures:
        figure["type"] = "figure"
    return figures


def nest_headline_figures(headline_figures):
    figures = list(headline_figures)
    for figure in figures:
        figure["type"] = "item"
    parent = {
        "id": str(uuid.uuid4()),
        "type": "figures",
        "value": figures,
    }

    return [parent]


def restructure_headline_figures_type(apps, schema_editor, processing_func):
    StatisticalArticlePage = apps.get_model("articles", "StatisticalArticlePage")
    Revision = apps.get_model("wagtailcore", "Revision")
    ContentType = apps.get_model("contenttypes", "ContentType")

    statistical_article_page_content_type = ContentType.objects.get_for_model(StatisticalArticlePage)

    for article_page in StatisticalArticlePage.objects.all():
        if article_page.headline_figures:
            article_page.headline_figures = processing_func(article_page.headline_figures.raw_data)
            article_page.save(update_fields=["headline_figures"])

    # Update the revisions
    revisions_to_update = Revision.objects.filter(content_type=statistical_article_page_content_type).iterator()

    for revision in revisions_to_update:
        if headline_figures_json := revision.content.get("headline_figures"):
            headline_figures_data = json.loads(headline_figures_json)
            if not headline_figures_data:
                continue
            headline_figures = processing_func(headline_figures_data)
            revision.content["headline_figures"] = json.dumps(headline_figures)
            revision.save(update_fields=["content"])


def migrate_statistical_article_pages_figures(apps, schema_editor):
    restructure_headline_figures_type(apps, schema_editor, denest_headline_figures)


def reverse_migrate_statistical_article_pages_figures(apps, schema_editor):
    restructure_headline_figures_type(apps, schema_editor, nest_headline_figures)


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0004_statisticalarticlepage_headline_figures_figure_ids"),
    ]

    operations = [
        migrations.RunPython(
            migrate_statistical_article_pages_figures, reverse_code=reverse_migrate_statistical_article_pages_figures
        ),
    ]
