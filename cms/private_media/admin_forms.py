from django import forms
from wagtail.documents.forms import BaseDocumentForm as WagtailBaseDocumentForm
from wagtail.images.forms import BaseImageForm as WagtailBaseImageForm


class BasePrivateDocumentForm(WagtailBaseDocumentForm):
    """Activated via the documented WAGTAILDOCS_DOCUMENT_FORM_BASE setting, this base
    form ensures that the custom fields introduced by AbstractPrivateDocument are
    included as hidden fields in all document edit forms.

    An overriden 'DocumentChooseView' will take care of populating the values in
    the 'creation' form, then they should be preserved and respected in all other
    views/forms.
    """

    class Meta:
        widgets = WagtailBaseDocumentForm.Meta.widgets.copy()
        widgets["parent_object_id"] = forms.HiddenInput()
        widgets["parent_object_content_type"] = forms.HiddenInput()
        widgets["parent_object_id_outstanding"] = forms.HiddenInput()


class BasePrivateImageForm(WagtailBaseImageForm):
    """Activated via the documented WAGTAILIMAGES_IMAGE_FORM_BASE setting, this base
    form ensures that the custom fields introduced by AbstractPrivateImage are
    included as hidden fields in all image edit forms.

    An overriden 'ImageChooseView' will take care of populating the values in
    the 'creation' form, then they should be preserved and respected in all other
    views/forms.
    """

    class Meta:
        widgets = WagtailBaseImageForm.Meta.widgets.copy()
        widgets["parent_object_id"] = forms.HiddenInput()
        widgets["parent_object_content_type"] = forms.HiddenInput()
        widgets["parent_object_id_outstanding"] = forms.HiddenInput()
