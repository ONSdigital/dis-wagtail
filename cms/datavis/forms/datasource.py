import csv
import io
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms.collections import BaseCollectionMemberForm
from wagtail.admin.forms.models import WagtailAdminModelForm

from cms.datavis.models import Visualisation
from cms.datavis.utils import numberfy

if TYPE_CHECKING:
    from wagtail.blocks import StreamValue


class DataSourceEditForm(WagtailAdminModelForm, BaseCollectionMemberForm):
    csv_file = forms.FileField(
        label=_("Populate from CSV"), required=False, widget=forms.FileInput(attrs={"accept": "text/csv"})
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        user = kwargs.get("for_user")
        super().__init__(*args, **kwargs)
        if not self.instance.pk and user:
            self.instance.created_by = user
            self.initial["created_by"] = user

    def clean(self) -> dict[str, Any]:
        data: dict[str, Any] = super().clean()
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
        return data

    @staticmethod
    def _extract_data_from_table_value(value: "StreamValue") -> Sequence[Sequence[str | int | float]]:
        if not value:
            return []
        # Decoding the json string value from the first block
        data: list[list[str | float | int]] = json.loads(value.raw_data[0]["value"]["table_data"])["data"]
        # Convert valid number strings to ints  floats
        if len(data) > 1:
            for row in data[1:]:
                for i, val in enumerate(row):
                    if isinstance(val, str):
                        row[i] = numberfy(val)
        return data

    def save(self, commit: bool = True) -> "Visualisation":
        instance: Visualisation = super().save(commit=False)
        if "csv_file" in self.changed_data or "table" in self.changed_data:
            instance.data = self._extract_data_from_table_value(instance.table)
            instance.column_count = len(instance.data[0])
            if commit:
                instance.save()
        return instance
