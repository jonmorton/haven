from dataclasses import dataclass

from .testutils import TestSetup


def test_union_type():
    @dataclass
    class Foo(TestSetup):
        x: float | str = 0.0

    foo = Foo.setup("x: 1.2")
    assert foo.x == 1.2

    foo = Foo.setup("x: bob")
    assert foo.x == "bob"
