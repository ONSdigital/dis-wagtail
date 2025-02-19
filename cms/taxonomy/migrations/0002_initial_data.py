# Generated by Django 5.1.6 on 2025-02-18 10:16

from django.db import migrations


def initial_data(apps, _schema_editor):
    Topic = apps.get_model("taxonomy", "Topic")

    # We cannot call Topic.add_root(...) here because the method is lost when retrieving the model through get_model
    # Instead we manually populate the path, depth and numchild fields, we should be safe to do this here because they
    # are simple and knowable for the first (and only) root node
    root_topic = Topic(
        id="_root",
        title="_Root Topic",
        description="Dummy root topic",
        path="0001",  # or another valid path for your tree
        depth=1,
        numchild=0,
    )
    root_topic.save()


class Migration(migrations.Migration):
    dependencies = [
        ("taxonomy", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(initial_data, migrations.RunPython.noop),
    ]
