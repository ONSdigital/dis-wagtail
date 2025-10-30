from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks

from cms.datasets.views import DatasetChooserViewSet, dataset_chooser_viewset


@hooks.register("register_admin_viewset")
def register_dataset_chooser_viewset() -> DatasetChooserViewSet:
    return dataset_chooser_viewset


@hooks.register("insert_global_admin_js")
def insert_dataset_chooser_js() -> str:
    """Insert JavaScript for dataset chooser published filter functionality."""
    return format_html('<script src="{}"></script>', static("js/dataset-chooser.js"))
