from typing import Any

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.template.defaultfilters import filesizeformat
from wagtail.documents.forms import BaseDocumentForm

MAX_CHARACTER_LIMIT = 100


class ONSDocumentForm(BaseDocumentForm):
    # Override the title field to add max length validation
    title = forms.CharField(max_length=MAX_CHARACTER_LIMIT, help_text=f"Limited to {MAX_CHARACTER_LIMIT} characters.")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # TODO: revisit when https://github.com/wagtail/wagtail/issues/13973 and related are fixed
        if "file" in self.fields:
            supported_formats_text = ", ".join(settings.WAGTAILDOCS_EXTENSIONS).upper()

            if settings.DOCUMENTS_MAX_UPLOAD_SIZE:
                max_upload_size_text = filesizeformat(settings.DOCUMENTS_MAX_UPLOAD_SIZE)
                help_text = f"Supported formats: {supported_formats_text}. Maximum filesize: {max_upload_size_text}."
            else:
                help_text = f"Supported formats: {supported_formats_text}."

            self.fields["file"].help_text = help_text

    def clean_file(self) -> Any:
        file = self.cleaned_data.get("file")
        if not file:
            return file

        if file.size > settings.DOCUMENTS_MAX_UPLOAD_SIZE:
            max_upload_size_text = filesizeformat(settings.DOCUMENTS_MAX_UPLOAD_SIZE)
            raise ValidationError(f"File size must be less than {max_upload_size_text}.")

        # Validate file extension
        # TODO: revisit when https://github.com/wagtail/wagtail/issues/13973 and related are fixed
        supported_formats_text = ", ".join(settings.WAGTAILDOCS_EXTENSIONS).upper()
        validate = FileExtensionValidator(
            allowed_extensions=settings.WAGTAILDOCS_EXTENSIONS,
            message=f"Not a supported document format. Supported formats: {supported_formats_text}.",
            code="invalid_document_extension",
        )
        validate(file)

        return file
