import enum
from dataclasses import dataclass, field
from typing import List, Tuple, Type

from haven.type_inspector import is_enum, is_list, is_tuple, is_tuple_or_list_of_dataclasses

from .testutils import parametrize


@dataclass
class SomeDataclass:
    x: float = 123


@parametrize(
    "t",
    [
        Tuple[int, ...],
        Tuple[str],
        Tuple,
        tuple,
    ],
)
def test_is_tuple(t: Type):
    assert is_tuple(t)
    assert not is_list(t)


@parametrize(
    "t",
    [
        List[int],
        List[str],
        List,
        list,
        List[SomeDataclass],
    ],
)
def test_is_list(t: Type):
    assert is_list(t)
    assert not is_tuple(t)


@parametrize(
    "t",
    [
        List[SomeDataclass],
        Tuple[SomeDataclass],
    ],
)
def test_is_list_of_dataclasses(t: Type):
    assert is_tuple_or_list_of_dataclasses(t)


@dataclass
class A:
    a: str = "bob"


class Color(enum.Enum):
    RED = "RED"
    ORANGE = "ORANGE"
    BLUE = "BLUE"


class Temperature(enum.IntEnum):
    HOT = 1
    WARM = 0
    COLD = -1
    MONTREAL = -35


@parametrize(
    "t",
    [
        Color,
        Temperature,
    ],
)
def test_is_enum(t: Type):
    assert is_enum(t)


def test_list_field():
    @dataclass
    class A:
        a: List[str] = field(default_factory=["bob", "john", "bart"].copy)

    a1 = A()
    a2 = A()
    assert id(a1.a) != id(a2.a)
