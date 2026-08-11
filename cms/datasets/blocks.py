from collections import defaultdict

from django.conf import settings
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
)

from cms.core.blocks.struct_blocks import RelativeOrAbsoluteURLBlock
from cms.core.url_utils import extract_url_path, validate_ons_url_struct_block
from cms.datasets.views import dataset_chooser_viewset

DatasetChooserBlock = dataset_chooser_viewset.get_block_class(
    name="DatasetChooserBlock", module_path="cms.datasets.blocks"
)

DUPLICATE_DATASET_ERROR = 'Duplicate datasets are not allowed. Another entry links to "{url_path}".'

# Added for pages whose links resolve to an edition. The chooser lists the dataset version, so an
# editor who picked two versions of one edition needs telling why that counts as a duplicate.
LATEST_VERSION_DUPLICATE_HINT = (
    " Links from this page point to the latest published version of an edition, so the dataset "
    "version does not affect the destination."
)


class ManualDatasetBlock(StructBlock):
    title = CharBlock(required=True, required_on_save=True)
    description = TextBlock(required=False)
    url = RelativeOrAbsoluteURLBlock(
        required=True,
        help_text="Enter a relative URL (e.g. /some/path) or a full URL starting with 'https://' "
        f"that matches one of the allowed domains or their subdomains: {', '.join(settings.ONS_ALLOWED_LINK_DOMAINS)}",
        required_on_save=True,
    )

    class Meta:
        icon = "link"

    def clean(self, value: StructValue) -> StructValue:
        errors = validate_ons_url_struct_block(value, self.child_blocks)

        if errors:
            raise StructBlockValidationError(errors)

        return super().clean(value)


class DatasetStoryBlock(StreamBlock):
    dataset_lookup = DatasetChooserBlock(label="Lookup Dataset", required_on_save=True)
    manual_link = ManualDatasetBlock(
        required=False,
        label="Manually Linked Dataset",
    )

    class Meta:
        # Overridden per field: release calendar pages pass True so that looked up datasets link to
        # the latest published version of the chosen edition rather than the dataset series page.
        link_to_latest_version = False

    def clean(self, value: StreamValue) -> StreamValue:
        cleaned_value = super().clean(value)

        # Validate there are no duplicate datasets,
        # including between manual and looked up datasets referencing the same URL

        # For each dataset URL path, record the indices of the blocks it appears in.
        # Looked up datasets are compared by the destination they resolve to for this page rather
        # than by dataset ID, because the same dataset can resolve to different destinations.
        # Both kinds of block are then normalised the same way, so that a URL typed by hand is
        # recognised as a duplicate of a lookup resolving to the same place however it was written.
        url_paths = defaultdict(set)
        for block_index, block in enumerate(cleaned_value):
            url = (
                block.value.get_url_path(link_to_latest_version=self.meta.link_to_latest_version)
                if block.block_type == "dataset_lookup"
                else block.value["url"]
            )
            url_paths[extract_url_path(url).lower()].add(block_index)

        block_errors = {}
        for url_path, block_indices in url_paths.items():
            # Add a block error for any index which contains a duplicate URL,
            # so that the validation error messages appear on the actual duplicate entries
            if len(block_indices) > 1:
                message = DUPLICATE_DATASET_ERROR.format(url_path=url_path)
                if self.meta.link_to_latest_version:
                    message += LATEST_VERSION_DUPLICATE_HINT
                for index in block_indices:
                    block_errors[index] = ValidationError(message)

        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return cleaned_value
