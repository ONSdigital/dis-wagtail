from collections import defaultdict

from django.core.exceptions import ValidationError
from wagtail.blocks import (
    CharBlock,
    StreamBlock,
    StreamBlockValidationError,
    StreamValue,
    StructBlock,
    TextBlock,
    URLBlock,
)

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


class TimeSeriesPageLinkBlock(StructBlock):
    title = CharBlock(required=True)
    url = URLBlock(required=True)
    page_summary = TextBlock(required=True)

    class Meta:
        icon = "link"


class TimeSeriesPageStoryBlock(StreamBlock):
    time_series_page_link = TimeSeriesPageLinkBlock()

    def clean(self, value: StreamValue, ignore_required_constraints: bool = False) -> StreamValue:
        cleaned_value = super().clean(value)

        # For each dataset URL path, record the indices of the blocks it appears in
        url_paths = defaultdict(set)
        for block_index, block in enumerate(cleaned_value):
            url_paths[block.value["url"]].add(block_index)

        block_errors = {}
        for block_indices in url_paths.values():
            # Add a block error for any index which contains a duplicate a URL path, so that the validation error
            # messages appear on the actual duplicate entries
            if len(block_indices) > 1:
                for index in block_indices:
                    block_errors[index] = ValidationError("Duplicate time series links are not allowed")

        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return cleaned_value


class DatasetStoryBlock(StreamBlock):
    dataset_lookup = DatasetChooserBlock(label="Lookup Dataset")
    manual_link = ManualDatasetBlock(
        required=False,
        label="Manually Linked Dataset",
    )

    def clean(self, value: StreamValue, ignore_required_constraints: bool = False) -> StreamValue:
        cleaned_value = super().clean(value)

        # Validate there are no duplicate datasets, including between manual and looked up datasets referencing the same
        # URL path

        # For each dataset URL path, record the indices of the blocks it appears in
        url_paths = defaultdict(set)
        for block_index, block in enumerate(cleaned_value):
            if block.block_type == "dataset_lookup":
                # For dataset lookup blocks, use the website URL
                url_path = block.value.website_url
            else:
                block.value["url"] = block.value["url"].rstrip("/")
                url_path = block.value["url"]
            url_paths[url_path].add(block_index)

        block_errors = {}
        for block_indices in url_paths.values():
            # Add a block error for any index which contains a duplicate a URL path, so that the validation error
            # messages appear on the actual duplicate entries
            if len(block_indices) > 1:
                for index in block_indices:
                    block_errors[index] = ValidationError("Duplicate datasets are not allowed")

        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return cleaned_value
