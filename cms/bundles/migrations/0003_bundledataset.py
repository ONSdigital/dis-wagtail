# Generated by Django 5.1.8 on 2025-04-29 13:36

import django.db.models.deletion
import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bundles", "0002_bundleteam"),
        ("datasets", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BundleDataset",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="datasets.dataset"
                    ),
                ),
                (
                    "parent",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bundled_datasets",
                        to="bundles.bundle",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
    ]
