from wagtail import hooks

from cms.datasets.views import DatasetChooserViewSet, dataset_chooser_viewset


@hooks.register("register_admin_viewset")
def register_dataset_chooser_viewset() -> DatasetChooserViewSet:
    return dataset_chooser_viewset
