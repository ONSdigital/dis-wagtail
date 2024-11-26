from django import forms

from wagtail.documents.forms import BaseDocumentForm as WagtailBaseDocumentForm


class BaseDocumentForm(WagtailBaseDocumentForm):
    class Meta:
        widgets = WagtailBaseDocumentForm.Meta.widgets.copy()
        widgets["parent_object_id"] = forms.HiddenInput()
        widgets["parent_object_content_type"] = forms.HiddenInput()
        widgets["parent_object_id_outstanding"] = forms.HiddenInput()
