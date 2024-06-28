from collections.abc import Callable
from dataclasses import dataclass
from types import GenericAlias
from typing import Any, Optional, get_type_hints


@dataclass
class RegistryFunc:
    # The function saved in the registry
    func: Callable
    # Whether the function should be registered for subclasses as well
    include_subclasses: bool


class TypeRegistry:
    def __init__(self):
        self.registry = {}

    def dispatch(self, ty: Any) -> Optional[RegistryFunc]:
        try:
            impl = self.registry[ty]
        except KeyError:
            try:
                impl = _find_impl(ty, self.registry)
            except KeyError:
                return None

        return impl

    def register(self, ty: Any, func=None, include_subclasses=False):
        if func is None:
            if isinstance(ty, type):
                return lambda f: self.register(ty, func=f, include_subclasses=include_subclasses)
            ann = getattr(ty, "__annotations__", {})
            if not ann:
                raise TypeError(
                    f"Invalid first argument to `register()`: {ty!r}. "
                    f"Use either `@register(some_class)` or plain `@register` "
                    f"on an annotated function."
                )
            func = ty

            argname, ty = next(iter(get_type_hints(func).items()))
            assert isinstance(
                ty, type
            ), f"Invalid annotation for {argname!r}. {ty!r} is not a class."
        self.registry[ty] = RegistryFunc(func, include_subclasses)
        return func


# ================================================================================
# code below is copied from functools internals impl of "singledispatch"
# ================================================================================


def _find_impl(cls, registry):
    """Returns the best matching implementation from *registry* for type *cls*.

    Where there is no registered implementation for a specific type, its method
    resolution order is used to find a more generic implementation.

    Note: if *registry* does not contain an implementation for the base
    *object* type, this function may return None.

    """
    if not hasattr(cls, "__mro__"):
        return None
    mro = _compose_mro(cls, registry.keys())
    match = None
    for t in mro:
        if match is not None:
            # If *match* is an implicit ABC but there is another unrelated,
            # equally matching implicit ABC, refuse the temptation to guess.
            if (
                t in registry
                and t not in cls.__mro__
                and match not in cls.__mro__
                and not issubclass(match, t)
            ):
                raise RuntimeError(f"Ambiguous dispatch: {match} or {t}")
            break
        if t in registry:
            match = t
    return registry.get(match)


def _c3_merge(sequences):
    """Merges MROs in *sequences* to a single MRO using the C3 algorithm.

    Adapted from https://docs.python.org/3/howto/mro.html.

    """
    result = []
    while True:
        sequences = [s for s in sequences if s]  # purge empty sequences
        if not sequences:
            return result
        for s1 in sequences:  # find merge candidates among seq heads
            candidate = s1[0]
            for s2 in sequences:
                if candidate in s2[1:]:
                    candidate = None
                    break  # reject the current head, it appears later
            else:
                break
        if candidate is None:
            raise RuntimeError("Inconsistent hierarchy")
        result.append(candidate)
        # remove the chosen candidate
        for seq in sequences:
            if seq[0] == candidate:
                del seq[0]


def _c3_mro(cls, abcs=None):
    """Computes the method resolution order using extended C3 linearization.

    If no *abcs* are given, the algorithm works exactly like the built-in C3
    linearization used for method resolution.

    If given, *abcs* is a list of abstract base classes that should be inserted
    into the resulting MRO. Unrelated ABCs are ignored and don't end up in the
    result. The algorithm inserts ABCs where their functionality is introduced,
    i.e. issubclass(cls, abc) returns True for the class itself but returns
    False for all its direct base classes. Implicit ABCs for a given class
    (either registered or inferred from the presence of a special method like
    __len__) are inserted directly after the last ABC explicitly listed in the
    MRO of said class. If two implicit ABCs end up next to each other in the
    resulting MRO, their ordering depends on the order of types in *abcs*.

    """
    for i, base in enumerate(reversed(cls.__bases__)):
        if hasattr(base, "__abstractmethods__"):
            boundary = len(cls.__bases__) - i
            break  # Bases up to the last explicit ABC are considered first.
    else:
        boundary = 0
    abcs = list(abcs) if abcs else []
    explicit_bases = list(cls.__bases__[:boundary])
    abstract_bases = []
    other_bases = list(cls.__bases__[boundary:])
    for base in abcs:
        if issubclass(cls, base) and not any(issubclass(b, base) for b in cls.__bases__):
            # If *cls* is the class that introduces behaviour described by
            # an ABC *base*, insert said ABC to its MRO.
            abstract_bases.append(base)
    for base in abstract_bases:
        abcs.remove(base)
    explicit_c3_mros = [_c3_mro(base, abcs=abcs) for base in explicit_bases]
    abstract_c3_mros = [_c3_mro(base, abcs=abcs) for base in abstract_bases]
    other_c3_mros = [_c3_mro(base, abcs=abcs) for base in other_bases]
    return _c3_merge(
        [[cls]]
        + explicit_c3_mros
        + abstract_c3_mros
        + other_c3_mros
        + [explicit_bases]
        + [abstract_bases]
        + [other_bases]
    )


def _compose_mro(cls, types):
    """Calculates the method resolution order for a given class *cls*.

    Includes relevant abstract base classes (with their respective bases) from
    the *types* iterable. Uses a modified C3 linearization algorithm.

    """
    bases = set(cls.__mro__)

    # Remove entries which are already present in the __mro__ or unrelated.
    def is_related(typ):
        return (
            typ not in bases
            and hasattr(typ, "__mro__")
            and not isinstance(typ, GenericAlias)
            and issubclass(cls, typ)
        )

    types = [n for n in types if is_related(n)]

    # Remove entries which are strict bases of other entries (they will end up
    # in the MRO anyway.
    def is_strict_base(typ):
        for other in types:
            if typ != other and typ in other.__mro__:
                return True
        return False

    types = [n for n in types if not is_strict_base(n)]
    # Subclasses of the ABCs in *types* which are also implemented by
    # *cls* can be used to stabilize ABC ordering.
    type_set = set(types)
    mro = []
    for typ in types:
        found = []
        for sub in typ.__subclasses__():
            if sub not in bases and issubclass(cls, sub):
                found.append([s for s in sub.__mro__ if s in type_set])
        if not found:
            mro.append(typ)
            continue
        # Favor subclasses with the biggest number of useful bases
        found.sort(key=len, reverse=True)
        for sub in found:
            for subcls in sub:
                if subcls not in mro:
                    mro.append(subcls)
    return _c3_mro(cls, abcs=mro)
