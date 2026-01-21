import json

from django.db import migrations

MODELS_WITH_IMAGEBLOCK = [
    ("standard_pages", "InformationPage", "content"),
    ("articles", "StatisticalArticlePage", "content"),
    ("methodology", "MethodologyPage", "content"),
]


def migrate_imageblock_forward(apps, schema_editor):
    """Migrate ImageChooserBlock (raw ID) to ImageBlock (StructBlock)."""
    for app_label, model_name, field_name in MODELS_WITH_IMAGEBLOCK:
        Model = apps.get_model(app_label, model_name)
        # Migrates live page data
        _migrate_streamfield(Model, field_name, direction="forward")

    # Migrate revisions history
    _migrate_revisions(apps, direction="forward")


def migrate_imageblock_backward(apps, schema_editor):
    """Migrate ImageBlock (StructBlock) back to ImageChooserBlock (raw ID)."""
    for app_label, model_name, field_name in MODELS_WITH_IMAGEBLOCK:
        Model = apps.get_model(app_label, model_name)
        _migrate_streamfield(Model, field_name, direction="backward")

    # Migrate revisions
    _migrate_revisions(apps, direction="backward")


def _migrate_streamfield(Model, field_name, direction):
    """Iterate through all instances and migrate ImageBlock data."""
    for instance in Model.objects.all():
        field_value = getattr(instance, field_name, None)
        if not field_value:
            continue

        # StreamValue.raw_data returns a RawDataView
        stream_data = list(field_value.raw_data)
        modified = _process_blocks(stream_data, direction)

        if modified:
            setattr(instance, field_name, stream_data)
            instance.save(update_fields=[field_name])


def _migrate_revisions(apps, direction):
    """Migrate all revisions that contain ImageBlock data."""
    Revision = apps.get_model("wagtailcore", "Revision")

    for revision in Revision.objects.all():
        content = revision.content
        if not content or "content" not in content:
            continue

        stream_data = content["content"]

        # Revisions store StreamField as JSON string
        if isinstance(stream_data, str):
            try:
                stream_data = json.loads(stream_data)
            except (json.JSONDecodeError, TypeError):
                continue

        if not isinstance(stream_data, list):
            continue

        modified = _process_blocks(stream_data, direction)

        if modified:
            # Save back as JSON string
            content["content"] = json.dumps(stream_data)
            revision.content = content
            revision.save(update_fields=["content"])


def _process_blocks(blocks, direction):
    """Recursively process StreamField blocks to migrate ImageBlock data."""
    modified = False

    for block in blocks:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")
        block_value = block.get("value")

        if block_type == "image":
            if direction == "forward":
                # Old format: value is just an int (image PK)
                # New format: value is a dict with 'image' key
                if isinstance(block_value, int):
                    block["value"] = {
                        "image": block_value,
                        "figure_title": "",
                        "figure_subtitle": "",
                        "supporting_text": "",
                        "notes_section": "",
                        "download": False,
                    }
                    modified = True
            # backward
            # New format: value is a dict
            # Old format: value is just the image PK
            elif isinstance(block_value, dict) and "image" in block_value:
                block["value"] = block_value["image"]
                modified = True

        elif isinstance(block_value, list):
            # Nested StreamBlock (e.g., SectionContentBlock)
            if _process_blocks(block_value, direction):
                modified = True

        elif isinstance(block_value, dict):
            # Nested StructBlock (e.g., SectionBlock with 'content' key)
            for _, nested_value in block_value.items():
                if isinstance(nested_value, list) and _process_blocks(nested_value, direction):
                    modified = True

    return modified


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_rename_glossaryterm_to_definition"),
        ("standard_pages", "0003_cookiespage"),
        ("articles", "0008_articlesindexpage"),
        ("methodology", "0002_methodologiesindexpage"),
    ]

    operations = [
        migrations.RunPython(
            migrate_imageblock_forward,
            migrate_imageblock_backward,
        ),
    ]
