from typing import Any

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from wagtail.documents.forms import BaseDocumentForm

MAX_CHARACTER_LIMIT = 100
DOCUMENTS_MAX_UPLOAD_SIZE = settings.DOCUMENTS_MAX_UPLOAD_SIZE
DOCUMENTS_MAX_UPLOAD_SIZE_MB = DOCUMENTS_MAX_UPLOAD_SIZE / (1024 * 1024)


class ONSDocumentForm(BaseDocumentForm):
    # Override the title field to add max length validation
    title = forms.CharField(
        max_length=MAX_CHARACTER_LIMIT,
    )

    def clean_file(self) -> Any:
        file = self.cleaned_data.get("file")
        if file and file.size > DOCUMENTS_MAX_UPLOAD_SIZE:
            raise ValidationError(f"File size must be less than {DOCUMENTS_MAX_UPLOAD_SIZE_MB:.2f} MB.")
        return file
