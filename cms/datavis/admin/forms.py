import contextlib
import csv
import io
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms.collections import BaseCollectionMemberForm
from wagtail.admin.forms.models import WagtailAdminModelForm

from cms.datavis.models import Visualisation
from cms.datavis.utils import get_visualisation_type_choices, get_visualisation_type_model_from_name

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue


class DataSourceEditForm(WagtailAdminModelForm, BaseCollectionMemberForm):
    csv_file = forms.FileField(label=_("Populate from CSV"), required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.get("for_user")
        super().__init__(*args, **kwargs)
        if not self.instance.pk and user:
            self.instance.created_by = user
            self.initial["created_by"] = user

    def clean(self):
        data = super().clean()
        if file := data.get("csv_file"):
            csvfile = file.open("rb")
            try:
                textwrapper = io.TextIOWrapper(csvfile, encoding="utf-8", newline="")
                textwrapper.seek(0)
                reader = csv.reader(textwrapper)
                data["table"] = [
                    {
                        "type": "table",
                        "value": {
                            "table_data": json.dumps(
                                {
                                    "data": list(reader),
                                    "style": {},
                                    "table_type": "table",
                                }
                            ),
                        },
                    }
                ]
            finally:
                csvfile.close()

    @staticmethod
    def _extract_data_from_table_value(value: "StreamValue") -> Sequence[Sequence[str | float]]:
        if not value:
            return []
        # Decoding the json string value from the first block
        data = json.loads(value.raw_data[0]["value"]["table_data"])["data"]
        # Convert valid number strings to floats
        if len(data) > 1:
            for row in data[1:]:
                for i, val in enumerate(row):
                    if isinstance(val, str):
                        with contextlib.suppress(ValueError):
                            row[i] = float(val.strip())
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if "csv_file" in self.changed_data or "table" in self.changed_data:
            instance.data = self._extract_data_from_table_value(instance.table)
            instance.column_count = len(instance.data[0])
            if commit:
                instance.save()
        return instance


class VisualisationEditForm(WagtailAdminModelForm, BaseCollectionMemberForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.get("for_user")
        super().__init__(*args, **kwargs)
        if not self.instance.pk and user:
            self.instance.created_by = user
            self.initial["created_by"] = user


class VisualisationCopyForm(WagtailAdminModelForm, BaseCollectionMemberForm):
    new_type = forms.ChoiceField(choices=get_visualisation_type_choices, label=_("Create as"), required=True)

    class Meta:
        model = Visualisation
        fields: ClassVar[list[str]] = ["collection", "name", "new_type"]
        labels: ClassVar[dict[str, Any]] = {
            "name": _("New visualisation name"),
        }

    def __init__(self, *args, **kwargs):
        self.for_user = kwargs.get("for_user")
        super().__init__(*args, **kwargs)
        self.initial["new_type"] = self.instance.specific_class._meta.label_lower

    def save(self, commit=True):
        new_model = get_visualisation_type_model_from_name(self.cleaned_data["new_type"])
        original_field_values = {}
        for field in self.instance._meta.get_fields():
            if field.name not in [
                "visualisation_ptr",
                "id",
                "pk",
                "uuid",
                "created_at",
                "created_by",
                "updated_at",
                "content_type",
                "index_entries",
            ]:
                field_val = getattr(self.instance, field.name)
                # Special handling for 'inline' model values
                if hasattr(field_val, "get_object_list"):
                    field_val = field_val.get_object_list()
                original_field_values[field.name] = field_val

        # Replace self.instance with a new object of the correct type
        self.instance = new_model(**original_field_values)
        self.instance.created_by = self.for_user

        # Let the superclass handle saving of self.instance
        return super().save(commit)


class VisualisationTypeSelectForm(forms.Form):
    vis_type = forms.ChoiceField(
        choices=get_visualisation_type_choices, label=_("What type of chart do you want to create?"), required=True
    )
