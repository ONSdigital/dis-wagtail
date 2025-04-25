from typing import Any, ClassVar

from django import forms
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms.collections import BaseCollectionMemberForm
from wagtail.admin.forms.models import WagtailAdminModelForm

from cms.datavis.models import Visualisation
from cms.datavis.utils import get_child_model_from_name, get_creatable_visualisation_model_choices


class VisualisationTypeSelectForm(forms.Form):
    specific_type = forms.ChoiceField(
        choices=get_creatable_visualisation_model_choices,
        label=_("What type of visualisation would you like to create?"),
        required=True,
    )


class VisualisationEditForm(WagtailAdminModelForm, BaseCollectionMemberForm):
    instance: Visualisation

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        user = kwargs.get("for_user")
        super().__init__(*args, **kwargs)
        if not self.instance.pk and user:
            self.instance.created_by = user
            self.initial["created_by"] = user


class VisualisationCopyForm(WagtailAdminModelForm, BaseCollectionMemberForm):
    instance: Visualisation
    new_type = forms.ChoiceField(choices=get_creatable_visualisation_model_choices, label=_("Create as"), required=True)

    class Meta:
        model = Visualisation
        fields: ClassVar[list[str]] = ["collection", "name", "new_type"]
        labels: ClassVar[dict[str, Any]] = {
            "name": _("New visualisation name"),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.for_user = kwargs.get("for_user")
        super().__init__(*args, **kwargs)
        self.initial["new_type"] = self.instance.specific_class._meta.label_lower

    def save(self, commit: bool = True) -> "Visualisation":
        new_model = get_child_model_from_name(Visualisation, self.cleaned_data["new_type"])
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
                field_val: Any = getattr(self.instance, field.name)
                # Special handling for 'inline' model values
                if hasattr(field_val, "get_object_list"):
                    field_val = field_val.get_object_list()
                    for item in field_val:
                        item.pk = None
                original_field_values[field.name] = field_val

        # Replace self.instance with a new object of the chosen type
        self.instance = new_model(**original_field_values)  # type: ignore[assignment]
        self.instance.created_by = self.for_user

        # Let the superclass handle saving of self.instance
        return_val: Visualisation = super().save(commit)
        return return_val
