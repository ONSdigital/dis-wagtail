import factory.enums
from factory import Factory, faker, post_generation

from cms.taxonomy.models import Topic


class TopicFactory(Factory):
    class Meta:
        model = Topic
        strategy = factory.BUILD_STRATEGY  # To prevent Factory from trying to save the node

    id: str = faker.Faker("text", max_nb_chars=10)
    title: str = faker.Faker("sentence", nb_words=2)
    description: str = faker.Faker("sentence", nb_words=10)

    @post_generation
    def add_topic_as_root(obj: Topic, *_args, **_kwargs) -> None:
        """New root tree nodes need to be saved with add_root, so we use the BUILD_STRATEGY to skip the automatic save,
        and instead save the obj ourselves in this post generation hook.
        """
        Topic.add_root(instance=obj)
