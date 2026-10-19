# Taxonomy topics and the dummy root

Taxonomy topics are stored as a tree using [django-treebeard](https://django-treebeard.readthedocs.io/). Every real
topic sits under a single dummy root topic, which is created in a migration and is never shown to users.

This page explains when to use `Topic.objects.topics()` and when to use the unfiltered `Topic.objects` manager.

## Why there is a dummy root

Treebeard can hold several root nodes, but adding and moving a root uses different calls from adding and moving a
child (`add_root` instead of `add_child`, and sibling positions instead of a parent). Topics come from the Topic API
with an optional parent ID, and a topic can gain or lose its parent between syncs. Without a single root, every add
and move would need to branch on whether the topic has a parent.

So every top level topic is a child of one dummy root, with ID `_root`, created in the
`taxonomy/0002_initial_data` migration. A topic with no parent goes under the root, and the same `add_child` and
`move` calls work for every topic. This mirrors the Wagtail page tree, which also has a single root page above
everything.

```text
(dummy root)          depth 1, never shown
├── Economy           depth 2, a top level topic
│   └── Inflation     depth 3
└── People            depth 2
```

You can see this in `Topic.save_new` and `Topic.move`, where a missing parent falls back to the root:

```python
def move(self, target: Topic | None = None, pos: str = "sorted-child") -> None:
    """Move the topic to underneath the target parent. If no target is passed, move it underneath our root."""
    target_parent = target or Topic.objects.root_topic()
    super().move(target_parent, pos=pos)
```

The catch is that the dummy root is a real row in the `Topic` table, so a plain `Topic.objects.all()` returns it
alongside the real topics.

### Why the manager doesn't filter it out

Before the upgrade to treebeard 5, `TopicManager.get_queryset()` filtered the dummy root out, so `Topic.objects`
only ever returned real topics. That stopped working with treebeard 5, because treebeard resolves the tree through
`Topic.objects` internally and treebeard 5 leans on it more. For example, `add_child` now reloads the parent row
before adding to it:

```python
# treebeard/mp_tree.py, MP_AddChildHandler.process()
node = self.node_cls.objects.select_for_update().get(pk=self.node.pk)
```

When the parent is the dummy root and the manager hides it, that lookup raises `Topic.DoesNotExist`, so no top level
topic can be created. Treebeard has no hook to point it at a different manager.

So `Topic.objects` now returns every row, dummy root included, and callers choose whether to exclude it with
`topics()`.

## Which to use

| You want to                                       | Use                                     |
| ------------------------------------------------- | --------------------------------------- |
| List, count, filter or look up real topics        | `Topic.objects.topics()`                |
| Exclude the root from a queryset you already have | `.topics()` on the queryset             |
| Get the dummy root itself                         | `Topic.objects.root_topic()`            |
| Work with the tree structure itself               | `Topic.objects` (disable the lint rule) |

### Listing, counting and looking up topics

Use `topics()` for anything that shows, enumerates or looks up topics.

```python
from cms.taxonomy.models import Topic

# Good
all_topics = Topic.objects.topics()
topic_count = Topic.objects.topics().count()
topic = Topic.objects.topics().filter(id=topic_id).first()
active_ids = set(Topic.objects.topics().filter(removed=False).values_list("id", flat=True))

# Bad: these include the dummy root
all_topics = Topic.objects.all()
topic_count = Topic.objects.count()
topic = Topic.objects.filter(id=topic_id).first()
```

`topics()` also lives on the queryset, so it can come after a filter:

```python
Topic.objects.filter(removed=False).topics()
```

### Getting the dummy root

Use `root_topic()` rather than filtering on depth yourself:

```python
root = Topic.objects.root_topic()
root.add_child(instance=new_topic)
```

### Tree operations and other deliberate uses

Some code genuinely needs the root, for example tree operations, or checks that must also catch a clash with the
root's ID. Use the unfiltered manager, disable the lint rule on that line, and leave a comment explaining why:

```python
# Include the dummy root so a clash with its ID is still caught.
if Topic.objects.filter(id=topic.id).exists():  # pylint: disable=unfiltered-topic-queryset
    raise IntegrityError(f"Topic with id {topic.id} already exists")
```

## Foreign keys to Topic

A chooser widget only controls which topics are offered. It doesn't stop the dummy root being submitted. Any
`ForeignKey` to `Topic` needs `limit_choices_to` so form validation rejects it:

```python
from cms.taxonomy.models import DUMMY_ROOT_DEPTH, Topic

topic = models.ForeignKey(
    Topic,
    on_delete=models.SET_NULL,
    null=True,
    limit_choices_to={"depth__gt": DUMMY_ROOT_DEPTH},
)
```

## Lint rule

A custom pylint checker (`pylint_plugins/topics.py`) flags `unfiltered-topic-queryset` (`W9701`) when non-test code
uses:

- `Topic.objects` without chaining `.topics()` or `.root_topic()`
- `get_ancestors()`, `get_tree()` or `get_root_nodes()` on a `Topic` class or instance

It runs as part of `make lint-py` and the pre-commit hooks.

It doesn't catch everything, so these still need care:

- **Tests are not checked.** Assertions such as `Topic.objects.count()` will silently include the root. Use
  `Topic.objects.topics()` in tests too.
- **Anything pylint can't infer as a `Topic`**, such as raw SQL or querysets passed around without type information.

`cms/taxonomy/tests/test_models.py` also has a guard test, `test_default_manager_includes_root_topic`, which fails if
anyone filters the root out of the manager.
