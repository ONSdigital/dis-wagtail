import factory

from cms.teams.models import Team


class TeamFactory(factory.django.DjangoModelFactory):
    """Factory for the preview team."""

    identifier = factory.Faker("uuid4")
    name = factory.Faker("sentence", nb_words=4)

    class Meta:
        model = Team
