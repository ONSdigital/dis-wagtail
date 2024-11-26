from django import forms
from wagtail.images.forms import BaseImageForm as WagtailBaseImageForm


class BaseImageForm(WagtailBaseImageForm):
    class Meta:
        widgets = WagtailBaseImageForm.Meta.widgets.copy()
        widgets["parent_object_id"] = forms.HiddenInput()
        widgets["parent_object_content_type"] = forms.HiddenInput()
        widgets["parent_object_id_outstanding"] = forms.HiddenInput()
