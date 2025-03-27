from django.db import migrations


def disable_core_workflow(apps, schema_editor):
    Workflow = apps.get_model("wagtailcore.Workflow")
    WorkflowPage = apps.get_model("wagtailcore.WorkflowPage")

    workflow = Workflow.objects.get(pk=1)
    workflow.active = False
    workflow.save(update_fields=["active"])

    WorkflowPage.objects.filter(workflow=workflow).delete()


def enable_core_workflow(apps, schema_editor):
    Workflow = apps.get_model("wagtailcore.Workflow")
    WorkflowPage = apps.get_model("wagtailcore.WorkflowPage")
    Page = apps.get_model("wagtailcore.Page")

    workflow = Workflow.objects.get(pk=1)
    workflow.active = True
    workflow.save(update_fields=["active"])

    WorkflowPage.objects.create(workflow=workflow, page=Page.objects.first())


def create_tasks_and_workflow(apps, schema_editor):
    # Get models
    ContentType = apps.get_model("contenttypes.ContentType")
    Workflow = apps.get_model("wagtailcore.Workflow")
    WorkflowPage = apps.get_model("wagtailcore.WorkflowPage")
    WorkflowTask = apps.get_model("wagtailcore.WorkflowTask")
    Page = apps.get_model("wagtailcore.Page")
    GroupReviewTask = apps.get_model("workflows.GroupReviewTask")
    ReadyToPublishGroupTask = apps.get_model("workflows.ReadyToPublishGroupTask")

    review_task_content_type, _ = ContentType.objects.get_or_create(model="groupreviewtask", app_label="workflows")
    review_task = GroupReviewTask.objects.create(name="In Preview", content_type=review_task_content_type, active=True)

    ready_task_content_type, _ = ContentType.objects.get_or_create(
        model="readytopublishgrouptask", app_label="workflows"
    )
    ready_to_publish_task = ReadyToPublishGroupTask.objects.create(
        name="Ready to publish", content_type=ready_task_content_type, active=True
    )

    workflow = Workflow.objects.create(name="Release review", active=True)
    WorkflowTask.objects.create(workflow=workflow, task=review_task, sort_order=0)
    WorkflowTask.objects.create(workflow=workflow, task=ready_to_publish_task, sort_order=1)

    WorkflowPage.objects.create(workflow=workflow, page=Page.objects.first())


def remove_tasks_and_workflow(apps, schema_editor):
    Workflow = apps.get_model("wagtailcore.Workflow")
    GroupReviewTask = apps.get_model("workflows.GroupReviewTask")
    ReadyToPublishGroupTask = apps.get_model("workflows.ReadyToPublishGroupTask")

    GroupReviewTask.objects.all().delete()
    ReadyToPublishGroupTask.objects.all().delete()
    Workflow.objects.filter(name="Release review").delete()


class Migration(migrations.Migration):
    dependencies = [("workflows", "0001_initial")]

    operations = [
        migrations.RunPython(disable_core_workflow, enable_core_workflow),
        migrations.RunPython(create_tasks_and_workflow, remove_tasks_and_workflow),
    ]
