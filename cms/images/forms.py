from typing import Any

from wagtail.images.forms import BaseImageForm


class CustomImageForm(BaseImageForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "description" in self.fields:
            self.fields["description"].label = "Alternative Text"
            self.fields["description"].required = True
            self.fields[
                "title"
            ].help_text = "The title field will be used as the file name when the image is downloaded."
