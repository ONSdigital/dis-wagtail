from typing import TYPE_CHECKING, Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .models import Bundle, BundledPageMixin
from .viewsets import BundleChooserWidget

if TYPE_CHECKING:
    from wagtail.models import Page


class AddToBundleForm(forms.Form):
    """Administrative form used in the 'add to bundle' view."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.page_to_add: Page = kwargs.pop("page_to_add")

        super().__init__(*args, **kwargs)

        self.fields["bundle"] = forms.ModelChoiceField(
            queryset=Bundle.objects.editable(),
            widget=BundleChooserWidget(),
            label=_("Bundle"),
            help_text=_("Select a bundle for this page."),
        )

    def clean(self) -> None:
        super().clean()

        if not isinstance(self.page_to_add, BundledPageMixin):
            # While this form is used the "add to bundle" view which already checks for this,
            # it doesn't hurt to trust but verify.
            raise ValidationError(_("Pages of this type cannot be added."))

        bundle = self.cleaned_data.get("bundle")
        if bundle and bundle.bundled_pages.filter(page=self.page_to_add).exists():
            message = _("Page '%(page)s' is already in bundle '%(bundle)s'") % {
                "page": self.page_to_add.get_admin_display_title(),  # type: ignore[attr-defined]
                "bundle": bundle,
            }
            raise ValidationError({"bundle": message})
