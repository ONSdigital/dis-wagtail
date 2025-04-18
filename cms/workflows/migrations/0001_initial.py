# Generated by Django 5.1.7 on 2025-03-19 12:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]

    operations = [
        migrations.CreateModel(
            name="GroupReviewTask",
            fields=[
                (
                    "task_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.task",
                    ),
                ),
                ("groups", models.ManyToManyField(to="auth.group")),
            ],
            options={
                "verbose_name": "Group review task",
                "verbose_name_plural": "Group review tasks",
            },
            bases=("wagtailcore.task",),
        ),
        migrations.CreateModel(
            name="ReadyToPublishGroupTask",
            fields=[
                (
                    "task_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.task",
                    ),
                ),
                ("groups", models.ManyToManyField(to="auth.group")),
            ],
            options={
                "verbose_name": "Ready to publish task",
                "verbose_name_plural": "Ready to publish tasks",
            },
            bases=("wagtailcore.task",),
        ),
    ]
