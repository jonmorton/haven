from dataclasses import dataclass, field

import haven
from haven.utils import ParsingError

from tests.test_default_args import raises

from .testutils import TestSetup


def test_component():
    @dataclass
    class Base:
        name: str

    @dataclass
    class ChildA(Base):
        a: int = 5

    @dataclass
    class ChildB(Base):
        b: dict[str, str] = field(default_factory=dict)

    def a(cfg: ChildA):
        return str(cfg.a)

    def b(cfg: ChildB):
        return str(len(cfg.b))

    @dataclass
    class Test(TestSetup):
        something: haven.Component[Base, str] = haven.choice([a, b])

    obj = Test.setup("""
something:
  name: a
  a: 6
""")
    assert isinstance(obj.something.config, ChildA)
    assert obj.something() == "6"

    obj = Test.setup("""
something:
  name: b
  b:
    c: abc
    d: def
""")
    assert isinstance(obj.something.config, ChildB)
    assert obj.something() == "2"

    with raises(ParsingError):
        Test.setup("""
something:
  name: ChildC
""")


def test_choice_default():
    @dataclass
    class Base:
        name: str = "ChildA"

    @dataclass
    class ChildA(Base):
        a: int = 5

    @dataclass
    class ChildB(Base):
        b: dict[str, str] = field(default_factory=dict)

    @dataclass
    class Test(TestSetup):
        something: Base = haven.choice([ChildA, ChildB])

    obj = Test.setup("something:\n  a: 6")
    assert isinstance(obj.something, ChildA)
    assert obj.something.a == 6


def test_choice_import():
    from .test_pkg.base import Base

    @dataclass
    class Test(TestSetup):
        name: str = "child_a"
        something: haven.Component[Base, int] = haven.choice(
            choices={
                "child_a": "tests.test_pkg.mod.run",
                "child_b": "tests.test_pkg.mod2.run",
            },
            key_field="name",
        )

    obj = Test.setup("""
something:
  name: child_a
  a: 10
""")

    assert obj.something() == 10  # type: ignore


def test_choice_plugin_mod():
    from .test_pkg.base import Base

    @dataclass
    class Test(TestSetup):
        something: haven.Component[Base, int] = haven.plugin(
            discover_packages_path="tests.test_plugin.mods",
            attr="run",
            key_field="name",
        )
        name: str = "child_a"

    obj = Test.setup("""
something:
  name: a
  a: 10
""")

    assert obj.something() == 10  # type: ignore


def test_choice_plugin_pkg():
    from .test_pkg.base import Base

    @dataclass
    class Test(TestSetup):
        name: str = "b"
        something: Base = haven.plugin(
            discover_packages_path="tests.test_plugin.pkgs",
            attr="tasks",
            key_field="name",
            default_factory="tests.test_pkg.mod.Test",
        )

    obj = Test.setup("""
something:
  name: run1
""")

    assert obj.something.b == 3  # type: ignore
