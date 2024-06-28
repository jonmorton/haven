from dataclasses import dataclass, field
from enum import Enum, auto

import haven

from .testutils import parametrize


class Color(Enum):
    blue = auto()
    red = auto()


def test_encode_something(simple_attribute):
    some_type, _, expected_value = simple_attribute

    @dataclass
    class SomeClass:
        d: dict[str, some_type] = field(default_factory=dict)  # type: ignore
        l: list[tuple[some_type, some_type]] = field(default_factory=list)  # type: ignore
        t: dict[str, some_type | None] = field(default_factory=dict)  # type: ignore

    b = SomeClass()
    b.d.update({"hey": expected_value})
    b.l.append((expected_value, expected_value))
    b.t.update({"hey": None, "hey2": expected_value})

    assert haven.load_pytree(SomeClass, haven.dump_pytree(b)) == b


@parametrize("config_type", ["yaml", "json"])
def test_dump_load(simple_attribute, config_type):
    some_type, _, expected_value = simple_attribute

    @dataclass
    class SomeClass:
        val: some_type | None = None

    b = SomeClass(val=expected_value)

    data = haven.dump(b, config_type)

    new_b = haven.load(SomeClass, data, format=config_type)
    assert new_b == b

    new_b = haven.load(SomeClass, "", format=config_type)
    assert new_b != b


def test_dump_load_dicts(simple_attribute):
    some_type, _, expected_value = simple_attribute

    @dataclass
    class SomeClass:
        d: dict[str, some_type] = field(default_factory=dict)
        l: list[tuple[some_type, some_type]] = field(default_factory=list)
        t: dict[str, some_type | None] = field(default_factory=dict)

    b = SomeClass()
    b.d.update({"hey": expected_value})
    b.l.append((expected_value, expected_value))
    b.t.update({"hey": None, "hey2": expected_value})

    data = haven.dump(b)

    new_b = haven.load(SomeClass, data)
    assert new_b == b


def test_dump_load_enum(tmp_path):
    @dataclass
    class SomeClass:
        color: Color = Color.red

    b = SomeClass()
    data = haven.dump(b)

    new_b = haven.load(SomeClass, data)
    print(b)
    print(new_b)

    assert new_b == b


def test_super_nesting():
    @dataclass
    class Complicated:
        x: list[list[list[dict[int, tuple[int, float, str, list[float]]]]]] = field(
            default_factory=list
        )

    c = Complicated()
    c.x = [[[{0: (2, 1.23, "bob", [1.2, 1.3])}]]]
    assert haven.load_pytree(Complicated, haven.dump_pytree(c)) == c
