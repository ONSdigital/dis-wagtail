import factory

from cms.datasets.models import Dataset


class DatasetFactory(factory.django.DjangoModelFactory):
    """Factory for Dataset model."""

    class Meta:
        model = Dataset

    namespace = factory.Sequence(lambda n: f"namespace-{n}")
    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("sentence", nb_words=16)
    version = factory.Sequence(lambda n: f"Version {n}")
    edition = factory.Sequence(lambda n: f"Edition {n}")
