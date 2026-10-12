import re
from typing import TYPE_CHECKING

from astroid import nodes
from astroid.bases import Instance
from pylint.checkers import BaseChecker
from pylint.checkers.utils import safe_infer

if TYPE_CHECKING:
    from pylint.lint import PyLinter

TOPIC_QNAME = "cms.taxonomy.models.Topic"

ALLOWED_CHAIN_METHODS = frozenset({"topics", "root_topic"})

ROOT_INCLUDING_TREE_METHODS = frozenset({"get_ancestors", "get_tree", "get_root_nodes"})

IGNORED_MODULES = re.compile(r"(^|\.)(tests|functional_tests)(\.|$)")


def _is_topic(node: nodes.NodeNG, *, allow_instance: bool) -> bool:
    inferred = safe_infer(node)
    if isinstance(inferred, nodes.ClassDef) or (allow_instance and isinstance(inferred, Instance)):
        return bool(inferred.is_subtype_of(TOPIC_QNAME))
    return False


def _chain_reaches_allowed_method(node: nodes.Attribute) -> bool:
    current: nodes.NodeNG = node
    while True:
        parent = current.parent
        if isinstance(parent, nodes.Call) and parent.func is current:
            current = parent
        elif isinstance(parent, nodes.Attribute) and parent.expr is current:
            if parent.attrname in ALLOWED_CHAIN_METHODS:
                return True
            current = parent
        else:
            return False


class TopicQuerySetChecker(BaseChecker):
    name = "topic-queryset"
    msgs = {  # noqa: RUF012
        "W9701": (
            "%s includes the dummy root topic, chain .topics() to exclude it",
            "unfiltered-topic-queryset",
            "Code that lists, counts or looks up topics should use Topic.objects.topics(),"
            " or .topics() on the queryset."
            " Where the tree is needed, disable this rule and comment why.",
        ),
    }

    def visit_attribute(self, node: nodes.Call) -> None:
        if node.attrname == "objects":
            is_topic = _is_topic(node.expr, allow_instance=False)
        elif node.attrname in ROOT_INCLUDING_TREE_METHODS:
            is_topic = _is_topic(node.expr, allow_instance=True)
        else:
            return

        if not is_topic or IGNORED_MODULES.search(node.root().name) or _chain_reaches_allowed_method(node):
            return

        self.add_message("unfiltered-topic-queryset", node=node, args=(node.as_string(),))


def register(linter: PyLinter) -> None:
    if any(checker.name == TopicQuerySetChecker.name for checker in linter.get_checkers()):
        return

    linter.register_checker(TopicQuerySetChecker(linter))
