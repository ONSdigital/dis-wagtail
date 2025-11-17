from collections import defaultdict

from django.core.exceptions import ValidationError
from wagtail.blocks import (
    CharBlock,
    StreamBlock,
    StreamBlockValidationError,
    StreamValue,
    StructBlock,
    StructBlockValidationError,
    StructValue,
    TextBlock,
    URLBlock,
)

from cms.core.url_utils import get_url_path, validate_ons_url_struct_block
from cms.datasets.views import dataset_chooser_viewset

DatasetChooserBlock = dataset_chooser_viewset.get_block_class(
    name="DatasetChooserBlock", module_path="cms.datasets.blocks"
)


class ManualDatasetBlock(StructBlock):
    title = CharBlock(required=True)
    description = TextBlock(required=False)
    url = URLBlock(required=True)

    class Meta:
        icon = "link"

    def clean(self, value: "StructValue") -> "StructValue":
        errors = validate_ons_url_struct_block(value, self.child_blocks)

        if errors:
            raise StructBlockValidationError(errors)

        return super().clean(value)


class DatasetStoryBlock(StreamBlock):
    dataset_lookup = DatasetChooserBlock(label="Lookup Dataset")
    manual_link = ManualDatasetBlock(
        required=False,
        label="Manually Linked Dataset",
    )

    def clean(self, value: StreamValue, ignore_required_constraints: bool = False) -> StreamValue:
        cleaned_value = super().clean(value)

        # Validate there are no duplicate datasets,
        # including between manual and looked up datasets referencing the same URL

        # For each dataset URL path, record the indices of the blocks it appears in
        url_paths = defaultdict(set)
        for block_index, block in enumerate(cleaned_value):
            url_path = (
                block.value.url_path if block.block_type == "dataset_lookup" else get_url_path(block.value["url"])
            )
            url_paths[url_path].add(block_index)

        block_errors = {}
        for block_indices in url_paths.values():
            # Add a block error for any index which contains a duplicate URL,
            # so that the validation error messages appear on the actual duplicate entries
            if len(block_indices) > 1:
                for index in block_indices:
                    block_errors[index] = ValidationError("Duplicate datasets are not allowed")

        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return cleaned_value
