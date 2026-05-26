# Data migration to move ONSTableBlock `caption` data into the new `sub_heading` field, and back again on reverse.

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations

MODELS_WITH_ONS_TABLE_BLOCK = [
    ("standard_pages", "InformationPage", "content"),
    ("articles", "StatisticalArticlePage", "content"),
    ("methodology", "MethodologyPage", "content"),
]


def caption_to_sub_heading(block):
    value = block["value"]
    caption = value.get("caption", "")
    if not caption:
        return False
    value["sub_heading"] = caption
    value["caption"] = ""
    return True


def sub_heading_to_caption(block):
    value = block["value"]
    sub_heading = value.get("sub_heading", "")
    if not sub_heading:
        return False
    value["caption"] = sub_heading
    value["sub_heading"] = ""
    return True


def _process_blocks(blocks, mapper):
    """Recursively walk StreamField blocks, applying `mapper` to every `table` block."""
    modified = False

    for block in blocks:
        block_type = block.get("type")
        block_value = block.get("value")

        if block_type == "table" and isinstance(block_value, dict):
            if mapper(block):
                modified = True

        elif isinstance(block_value, list):
            if _process_blocks(block_value, mapper):
                modified = True

        elif isinstance(block_value, dict):
            for nested_value in block_value.values():
                if isinstance(nested_value, list) and _process_blocks(nested_value, mapper):
                    modified = True

    return modified


def _handle_page(page, field_name, mapper):
    field_value = getattr(page, field_name, None)
    if field_value is None:
        return

    stream_data = list(field_value.raw_data)
    if _process_blocks(stream_data, mapper):
        setattr(page, field_name, json.dumps(stream_data, cls=DjangoJSONEncoder))
        page.save(update_fields=[field_name])


def _handle_revision(revision, field_name, mapper):
    content = revision.content
    if not content or field_name not in content:
        return

    raw_stream = content[field_name]
    if not raw_stream:
        return

    try:
        stream_data = json.loads(raw_stream)
    except (json.JSONDecodeError, TypeError):
        return

    if _process_blocks(stream_data, mapper):
        content[field_name] = json.dumps(stream_data, cls=DjangoJSONEncoder)
        revision.content = content
        revision.save(update_fields=["content"])


def _migrate(apps, mapper):
    Revision = apps.get_model("wagtailcore", "Revision")

    for app_label, model_name, field_name in MODELS_WITH_ONS_TABLE_BLOCK:
        Model = apps.get_model(app_label, model_name)
        for page in Model.objects.iterator():
            _handle_page(page, field_name, mapper)
            for revision in Revision.objects.filter(object_id=page.id).iterator():
                _handle_revision(revision, field_name, mapper)


def forwards(apps, schema_editor):
    _migrate(apps, caption_to_sub_heading)


def backwards(apps, schema_editor):
    _migrate(apps, sub_heading_to_caption)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_allow_officers_to_delete"),
        ("standard_pages", "0005_remove_indexpage_content_and_more"),
        ("articles", "0008_articlesindexpage"),
        ("methodology", "0002_methodologiesindexpage"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
