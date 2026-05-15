from typing import Any

from django.forms import ValidationError
from PIL.Image import DecompressionBombError
from wagtail.images.forms import BaseImageForm


class CustomImageForm(BaseImageForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "description" in self.fields:
            self.fields["description"].label = "Alternative text"
            self.fields["description"].required = True
            self.fields[
                "title"
            ].help_text = "The title field will be used as the file name when the image is downloaded."

    def full_clean(self) -> None:
        # HACK: Catch the decompression bomb error during clean, without modifying the field.
        # Remove when https://github.com/wagtail/wagtail/pull/14225 is merged.
        try:
            super().full_clean()
        except DecompressionBombError:
            self.add_error(
                "file",
                ValidationError(
                    self.fields["file"].error_messages["file_too_many_pixels"]
                    % {"num_pixels": "unknown number", "max_pixels_count": self.fields["file"].max_image_pixels},
                    code="file_too_many_pixels",
                ),
            )
