from wagtail import hooks

from cms.datasets.views import dataset_chooser_viewset


@hooks.register("register_admin_viewset")
def register_dataset_chooser_viewset():
    return dataset_chooser_viewset
