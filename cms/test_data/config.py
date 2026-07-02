from typing import Annotated, Self

import annotated_types
from faker import Faker
from pydantic import BaseModel, ConfigDict, NonNegativeInt, PositiveInt, model_validator

FractionalFloat = Annotated[float, annotated_types.Ge(0), annotated_types.Le(1)]


class BaseConfigModel(BaseModel):
    """A base model which ensures unknown fields raise an error."""

    model_config = ConfigDict(extra="forbid")


class RangeConfig(BaseConfigModel):
    min: NonNegativeInt = 1
    max: PositiveInt

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.min == self.max:
            raise ValueError("Range is unnecessary")
        if self.min > self.max:
            raise ValueError("min must be less than max")
        return self


class ModelCreationConfig(BaseConfigModel):
    count: PositiveInt | RangeConfig = 1


class PageCreationConfig(ModelCreationConfig):
    published_probability: FractionalFloat = 0.5
    revisions: PositiveInt | RangeConfig = 1


class TopicCreationConfig(PageCreationConfig):
    datasets: NonNegativeInt | RangeConfig = 1
    dataset_manual_links: NonNegativeInt = 0
    explore_more: NonNegativeInt | RangeConfig = 1


class TestDataConfig(BaseConfigModel):
    datasets: ModelCreationConfig = ModelCreationConfig()
    images: ModelCreationConfig = ModelCreationConfig()
    topics: TopicCreationConfig = TopicCreationConfig(count=3)

    def get_count(self, data: int | RangeConfig, faker: Faker) -> int:
        if isinstance(data, int):
            return data

        return faker.random_int(min=data.min, max=data.max)
