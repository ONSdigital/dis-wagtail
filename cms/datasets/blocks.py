from django.core.exceptions import ValidationError
from wagtail.blocks import (
    CharBlock,
    StreamBlock,
    StreamValue,
    StructBlock,
    StructBlockValidationError,
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
        template = "templates/components/streamfield/dataset_link_block.html"


class DatasetStoryBlock(StreamBlock):
    dataset_lookup = DatasetChooserBlock(
        label="Lookup Dataset", template="templates/components/streamfield/dataset_link_block.html"
    )
    manual_link = ManualDatasetBlock(
        required=False,
        label="Manually Linked Dataset",
    )

    class Meta:
        template = "templates/components/streamfield/datasets_block.html"

    def clean(self, value: StreamValue) -> StreamValue:
        cleaned_value = super().clean(value)

        # Check for duplicate datasets selected through the chooser
        chosen_datasets = [block.value for block in cleaned_value.blocks_by_name("dataset_lookup")]
        if len(chosen_datasets) != len(set(chosen_datasets)):
            raise StructBlockValidationError(non_block_errors=[ValidationError("Duplicate datasets are not allowed")])

        return cleaned_value
