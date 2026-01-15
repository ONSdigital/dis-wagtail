from typing import Annotated, Self

import annotated_types
from faker import Faker
from pydantic import BaseModel, PositiveInt, model_validator

FractionalFloat = Annotated[float, annotated_types.Ge(0), annotated_types.Le(0)]


class RangeConfig(BaseModel):
    min: PositiveInt = 1
    max: PositiveInt

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.min == self.max:
            raise ValueError("Range is unnecessary")
        if self.min > self.max:
            raise ValueError("min must be less than max")
        return self


class ModelCreationConfig(BaseModel):
    count: PositiveInt | RangeConfig = 1

    def get_count(self, faker: Faker) -> int:
        return get_count(self.count, faker)


def get_count(data: PositiveInt | RangeConfig, faker: Faker) -> int:
    if isinstance(data, int):
        return data

    return faker.random_int(min=data.min, max=data.max)


class PageCreationConfig(ModelCreationConfig):
    published: FractionalFloat = 0.5


class TopicCreationConfig(PageCreationConfig):
    datasets: PositiveInt | RangeConfig = 1
    dataset_manual_links: PositiveInt = 0
    explore_more: PositiveInt | RangeConfig = 1

    def datasets_count(self, faker: Faker) -> int:
        return get_count(self.datasets, faker)

    def explore_more_count(self, faker: Faker) -> int:
        return get_count(self.explore_more, faker)


class TestDataConfig(BaseModel):
    datasets: ModelCreationConfig = ModelCreationConfig()
    images: ModelCreationConfig = ModelCreationConfig()
    topics: TopicCreationConfig = TopicCreationConfig(count=3)
