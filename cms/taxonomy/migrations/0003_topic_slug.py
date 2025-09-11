from django.db import migrations, models


def set_temp_slugs(apps, schema_editor):
    Topic = apps.get_model("taxonomy", "Topic")
    for topic in Topic.objects.all():
        topic.slug = f"temp-{topic.id}"
        topic.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("taxonomy", "0002_initial_data"),
    ]

    operations = [
        # 1. Add the field (nullable so migration doesn’t fail)
        migrations.AddField(
            model_name="topic",
            name="slug",
            field=models.SlugField(max_length=100, null=True, blank=True),
        ),
        # 2. Populate it with a temporary value for existing rows
        migrations.RunPython(set_temp_slugs, migrations.RunPython.noop),
        # 3. Make it non-nullable after it's filled
        migrations.AlterField(
            model_name="topic",
            name="slug",
            field=models.SlugField(max_length=100, null=False),
        ),
    ]
