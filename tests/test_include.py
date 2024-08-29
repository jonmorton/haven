from dataclasses import dataclass, field

import haven
from _pytest.cacheprovider import os

from .testutils import TestSetup


def test_union_type():
    @dataclass
    class Child:
        name: str

    @dataclass
    class Foo(TestSetup):
        x: float = 0.0
        child: Child = field(default_factory=lambda: Child("test"))

    haven.set_include_base_dir(os.path.dirname(__file__))

    foo = Foo.setup("child: !include included.yaml")
    assert foo.x == 0.0
    assert foo.child.name == "Bob"
