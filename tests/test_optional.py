from dataclasses import dataclass, field

from tests.testutils import TestSetup


@dataclass
class Child:
    name: str = "Kevin"
    age: int = 12


@dataclass
class Dog:
    breed: str = "Saint Bernard"
    dog_years: int = 49


@dataclass
class Parent(TestSetup):
    child: Child | None = None
    dog: Dog | None = None


def test_optional_parameter_group():
    """Reproduces issue #28 :
    https://github.com/lebrice/SimpleParsing/issues/28#issue-663689719
    """
    parent: Parent = Parent.setup(overrides=["dog.breed=Shitzu"])
    assert parent.dog == Dog(breed="Shitzu")
    assert parent.child is None

    parent: Parent = Parent.setup(overrides=["child.name=Dylan"])
    assert parent.dog is None
    assert parent.child == Child(name="Dylan")

    parent: Parent = Parent.setup(overrides=["child.name=Dylan", "dog.dog_years=27"])
    assert parent.dog == Dog(dog_years=27)
    assert parent.child == Child(name="Dylan")


@dataclass
class GrandParent(TestSetup):
    niece: Parent | None = None
    nephew: Parent | None = None


# @pytest.mark.xfail(reason="TODO: Deeper nesting doesn't work atm!")
def test_deeply_nested_optional_parameter_groups():
    """Same as above tests, but deeper hierarchy."""
    grandparent: GrandParent = GrandParent.setup()
    assert grandparent.niece is None
    assert grandparent.nephew is None

    grandparent: GrandParent = GrandParent.setup(overrides=["niece.child.name=Bob"])
    assert grandparent.niece == Parent(child=Child(name="Bob"))
    assert grandparent.nephew is None


def test_optional_int():
    @dataclass
    class Bob(TestSetup):
        num_workers: int | None = 12

    assert Bob.setup("") == Bob(num_workers=12)
    assert Bob.setup("num_workers: null") == Bob(num_workers=None)
    assert Bob.setup("num_workers: 123") == Bob(num_workers=123)


def test_optional_str():
    @dataclass
    class Bob(TestSetup):
        a: str | None = "123"

    assert Bob.setup("a: null") == Bob(a=None)
    assert Bob.setup("a: 123") == Bob(a="123")
    assert Bob.setup("a: none") == Bob(a="none")


#
# @pytest.mark.xfail(reason=f"TODO: Rework the code to parsers containers.")
def test_optional_list_of_ints():
    @dataclass
    class Bob(TestSetup):
        a: list[int] | None = field(default_factory=list)

    assert Bob.setup("a: [1]") == Bob(a=[1])
    assert Bob.setup("a: [1,2,3]") == Bob(a=[1, 2, 3])
    assert Bob.setup("a: []") == Bob(a=[])
    assert Bob.setup("") == Bob(a=[])


def test_optional_without_default():
    @dataclass
    class Bob(TestSetup):
        a: int | None

    assert Bob.setup("a: null") == Bob(a=None)
    assert Bob.setup("a: 123") == Bob(a=123)
