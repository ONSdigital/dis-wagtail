import factory
import wagtail_factories

from cms.datasets.blocks import DatasetChooserBlock, DatasetStoryBlock, ManualDatasetBlock
from cms.datasets.models import Dataset


class DatasetFactory(factory.django.DjangoModelFactory):
    """Factory for Dataset model."""

    class Meta:
        model = Dataset
        django_get_or_create = ("namespace", "edition", "version")

    namespace = factory.Faker("sentence", nb_words=4)
    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("sentence", nb_words=16)
    version = factory.Sequence(lambda n: n)
    edition = factory.Sequence(lambda n: f"Edition {n}")


class DatasetChooserBlockFactory(wagtail_factories.blocks.ChooserBlockFactory):  # pylint: disable=no-member
    dataset = factory.SubFactory(DatasetFactory)

    class Meta:
        model = DatasetChooserBlock

    @classmethod
    def _build(cls, _model_class, dataset):
        return dataset

    @classmethod
    def _create(cls, _model_class, dataset):
        return dataset


class ManualDatasetBlockFactory(wagtail_factories.StructBlockFactory):
    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("sentence", nb_words=16)
    url = factory.Faker("url")

    class Meta:
        model = ManualDatasetBlock


class DatasetStoryBlockFactory(wagtail_factories.StreamBlockFactory):
    dataset_lookup = factory.SubFactory(DatasetChooserBlockFactory)
    manual_link = factory.SubFactory(ManualDatasetBlockFactory)

    class Meta:
        model = DatasetStoryBlock
