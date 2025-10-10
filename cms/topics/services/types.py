from typing import TypedDict, TypeVar

from cms.articles.models import StatisticalArticlePage
from cms.methodology.models import MethodologyPage

T = TypeVar("T")


class InternalArticleDict(TypedDict, total=False):
    internal_page: StatisticalArticlePage
    title: str


class ExternalArticleDict(TypedDict):
    url: str
    title: str
    description: str
    is_external: bool


class MethodologyDict(TypedDict):
    internal_page: MethodologyPage


ArticleDict = InternalArticleDict | ExternalArticleDict
