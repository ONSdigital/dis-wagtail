from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .models import Bundle
from .viewsets import BundleChooserWidget


class AddToBundleForm(forms.Form):
    """Administrative form used in the 'add to bundle' view."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.page_to_add = kwargs.pop("page_to_add")

        super().__init__(*args, **kwargs)

        self.fields["bundle"] = forms.ModelChoiceField(
            queryset=Bundle.objects.editable(),
            widget=BundleChooserWidget(),
            label=_("Bundle"),
            help_text=_("Select a bundle for this page."),
        )

    def clean(self) -> None:
        super().clean()

        bundle = self.cleaned_data.get("bundle")
        if bundle and bundle.bundled_pages.filter(page=self.page_to_add).exists():
            raise ValidationError(
                {"bundle": f"Page {self.page_to_add.get_admin_display_title()} is already in bundle '{bundle}'"}
            )
