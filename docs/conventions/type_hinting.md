# Python Type Hinting

As a team we have committed to adding type hints throughout the Python code. This document defines our approach to type hinting, to ensure consistency in the
codebase and avoid repeating discussions about how we apply typing.

## Variables

Specify types for variables initialised with `None`:

```python
description: Optional[str] = None
```

Specify types for empty collections:

```python
items: list[str] = []
mappings: dict[str, int] = {}
```

## Standard collections

For standard collections, use lower case names e.g `list` rather than `List`:

```python
items: list[int] = [1]
mappings: set[int] = {1, 2}
```

<https://www.python.org/dev/peps/pep-0585/>

## Generic types

Specify at least the top-level type parameters for generic types:

```python
def get_objects_matching(ids: Sequence[str]) -> dict[int, dict]
```

If the typing used for a generic type would be Any or indeterministic, do not specify it:

```python
items: list[Any] = ["demo", 2, True]  # Incorrect
items: list[str | int | bool] = ["demo", 2, True]  # Incorrect
items: list = ["demo", 2, True]  # Correct
```

This same ruling applies for key-val types such as `Mapping`.

If the key type and value types are known, they may be specified:

```python
known_types_dict: dict[str, str] = {"name": "demo"}
```

If the key type is known, and the value types are deterministic, use TypedDict:

```python
from typing import TypedDict

class Movie(TypedDict):
    name: str
    year: int
```

If the key type is known but the value types are indeterministic or the key type is not known, do not declare the types:

```python
json_data: dict = json.loads(stringified_json)
```

## Optional arguments

For arguments that can be a single type or None, use the shorthand `|` instead of using the older `Optional` keyword:

```python
def test(self, var: None | int) -> None:
```

For arguments that can be one of multiple types or None, use the shorthand `|` instead of using the older `Union` keyword:

```python
def test(self, var: None | int | str) -> None:
```

## Abstract vs concrete

-   Make argument types as abstract as possible (to be flexible to callers)
-   Make return types as specific as possible (to be predictable to callers)

```python
def increment_values(self, values: Sequence[int]) -> list[int]:
    return [value + 1 for value in values]
```

## Self Type

To annotate methods that return an instance of their class, use the `Self` type is as it is bound to it's encapsulating class. In the example below, the type
checker will correctly infer the type of `Circle().set_scale(0.5)` to be `Circle`:

```python
from typing import Self


class Shape:
    def set_scale(self, scale: float) -> Self:
        self.scale = scale
        return self


class Circle(Shape):
    def set_radius(self, radius: float) -> Self:
        self.radius = radius
        return self
```

This is recommended as forward declarations are now redundant in 3.10
<https://peps.python.org/pep-0673/>

## Type Alias

Use the special annotation `TypeAlias` to declare type aliases more explicitly so type checkers are able to distinguish between type aliases and ordinary
assignments:

```python
MyType: TypeAlias = "ClassName"


def foo() -> MyType: ...
```

## Type Ignore

To mark portions of the program that should not be covered by type hinting, use `# type: ignore` on the specific line. When used in a line by itself at the top
of a file, it silences all errors in the file:

```python
# type: ignore
```

`# type: ignore` should only be used when unavoidable (or in the return `Any` case detailed below).
Ensure that a comment is added to explain why it has been used and have a prefix of `Type ignore:`

```python
def format_number(number: int) -> str:
    # Type ignore: babel.format_number is untyped therefore returns Any.
    formatted_number: str = babel.format_number(number)  # type: ignore
    return formatted_number
```

The `warn_return_any` flag is turned on to force type hinting the return types for third party libraries and increase the safety of the code base.

Where type hints aren’t specific enough to identify the return type (e.g. objects like blocks where some keys correspond to strings,
others to lists, others to dicts) mypy will complain if you assume the type of any attribute:

```python
def get_id_from_block(block: dict) -> str:
    return block["id"] # Returning Any from function declared to return "str"
```

A type ignore can be avoided here, by changing the code to this...

```python
def get_id_from_block(block: dict) -> str:
    block_id: str = block["id"]
    return block_id
```

...but as this is a common pattern in a number of places, it results in a lot of duplicating the return type, and
extra lines of code for the sake of type hinting. In this scenario, it is ok to type ignore it.

If the value was needed for any other checks e.g.

```python
def get_first_answer_from_block(block: dict) -> str:
    answer = ...
    if answer["id"] ... :
        ...
    return answer
```

This would not be suitable to type ignore, and it should use the existing convention of typing the unknown variable:

```python
def get_first_answer_from_block(block: dict) -> str:
    answer: Answer = ...
    if answer["id"] ... :
        ...
    return answer
```

## ParamSpec

Use to forward the parameter types of one callable to another callable.

E.g. a basic logging function decorator:

```python
T = TypeVar("T")
P = ParamSpec("P")


def add_logging(f: Callable[P, T]) -> Callable[P, T]:
    """A type-safe decorator to add logging to a function."""

    def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        logging.info(f"{f.__name__} was called")
        return f(*args, **kwargs)

    return inner


@add_logging
def add_two(x: float, y: float) -> float:
    """Add two numbers together."""
    return x + y
```

## TypeVar

Use `TypeVar` when the type returned by a function is the same as the type which was passed in:

```python
T = TypeVar("T")

def increment_value(self, value: T) -> T:
    return value + 1
```

`TypeVar` also accepts extra positional arguments to restrict the type parameter for improving code documentation and error prevention.

```python
T = TypeVar("T", int, float)


def increment_value(self, value: T) -> T:
    return value + 1
```

## Useful links

-   <https://www.python.org/dev/peps/pep-0484/>
-   <https://www.pythonsheets.com/notes/python-typing.html>
-   <https://google.github.io/styleguide/pyguide.html#319-type-annotations>
