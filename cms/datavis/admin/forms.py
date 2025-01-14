import contextlib
import csv
import io
import json
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms.collections import BaseCollectionMemberForm
from wagtail.admin.forms.models import WagtailAdminModelForm

from cms.datavis.models import Visualisation
from cms.datavis.utils import get_visualisation_type_choices

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


class VisualisationCopyForm(WagtailAdminModelForm, BaseCollectionMemberForm):
    class Meta:
        model = Visualisation
        fields: ClassVar[list[str]] = ["collection", "name"]
        labels: ClassVar[dict[str, Any]] = {
            "name": _("New visualisation name"),
        }

    def __init__(self, *args, **kwargs):
        self.for_user = kwargs.get("for_user")
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        # Override values to create a new draft object
        self.instance.id = None
        self.instance.pk = None
        self.instance.uuid = uuid.uuid4()
        self.instance.live = False
        self.instance.created_at = None
        self.instance.created_by = self.for_user
        self.instance.updated_at = None
        self.instance._state.adding = True  # pylint: disable=protected-access
        return super().save(commit)


class VisualisationTypeSelectForm(forms.Form):
    vis_type = forms.ChoiceField(
        choices=get_visualisation_type_choices, label=_("What type of chart do you want to create?"), required=True
    )
