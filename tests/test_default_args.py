from dataclasses import dataclass

import haven
from haven.formats import decode_yaml

from .testutils import ParsingError, raises


def test_no_default_argument(simple_attribute):
    some_type, passed_value, expected_value = simple_attribute

    @dataclass
    class SomeClass:
        a: some_type

    cfg = haven.load(SomeClass, decode_yaml({"a": expected_value}))

    assert cfg == SomeClass(a=expected_value)

    with raises(ParsingError):
        haven.load_pytree(SomeClass, {})


def test_default_dataclass_argument(simple_attribute, silent):
    some_type, passed_value, expected_value = simple_attribute

    @dataclass
    class SomeClass:
        a: some_type = expected_value

    cfg = haven.load(SomeClass, "")
    assert cfg == SomeClass(a=expected_value)
