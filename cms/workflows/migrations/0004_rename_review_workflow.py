from django.db import migrations


def rename_workflow(apps, schema_editor):
    Workflow = apps.get_model("wagtailcore", "Workflow")
    Workflow.objects.using(schema_editor.connection.alias).filter(name="Release review").update(name="Review")


def restore_workflow_name(apps, schema_editor):
    Workflow = apps.get_model("wagtailcore", "Workflow")
    Workflow.objects.using(schema_editor.connection.alias).filter(name="Review").update(name="Release review")


class Migration(migrations.Migration):
    dependencies = [
        ("workflows", "0003_add_workflow_unlock_permission"),
    ]

    operations = [
        migrations.RunPython(rename_workflow, restore_workflow_name),
    ]
