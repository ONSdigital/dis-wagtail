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

# Appended on pages whose links resolve to an edition. The chooser lists the dataset version, so an
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
        # Set per field, and the only place a page declares where its dataset links go. It drives
        # both the duplicate check below and the URLs format_datasets_as_document_list renders,
        # which is what stops a page validating against one destination and rendering another.
        # Release calendar pages set True, so looked up datasets link to the latest published
        # version of the chosen edition rather than to the dataset series page.
        link_to_latest_version = False

    def clean(self, value: StreamValue, ignore_required_constraints: bool = False) -> StreamValue:
        cleaned_value = super().clean(value)

        # Validate there are no duplicate datasets, including between manual and looked up datasets
        # that point at the same place, however each was written. Destination resolution only
        # happens for looked up datasets: a manual link's URL is not resolved, so the version it
        # names is not dropped from it.
        #
        # url_paths maps a normalised comparison key to the blocks using it. That key is lowercased
        # and has its trailing slash stripped, so it is not fit to show an editor: destinations
        # holds the URL each group really links to, preferring a looked up dataset because the CMS
        # resolves that one itself rather than taking it from whatever somebody typed.
        url_paths = defaultdict(set)
        destinations: dict[str, str] = {}
        for block_index, block in enumerate(cleaned_value):
            is_lookup = block.block_type == "dataset_lookup"
            url = (
                block.value.get_url_path(link_to_latest_version=self.meta.link_to_latest_version)
                if is_lookup
                else block.value["url"]
            )
            url_path = extract_url_path(url).lower()
            url_paths[url_path].add(block_index)
            if is_lookup or url_path not in destinations:
                destinations[url_path] = url if is_lookup else extract_url_path(url)

        block_errors = {}
        for url_path, block_indices in url_paths.items():
            # Add a block error for any index which contains a duplicate URL,
            # so that the validation error messages appear on the actual duplicate entries
            if len(block_indices) > 1:
                message = DUPLICATE_DATASET_ERROR.format(url_path=destinations[url_path])
                if self.meta.link_to_latest_version:
                    message += LATEST_VERSION_DUPLICATE_HINT
                for index in block_indices:
                    block_errors[index] = ValidationError(message)

        if block_errors:
            raise StreamBlockValidationError(block_errors=block_errors)

        return cleaned_value
