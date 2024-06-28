"""Utilities for inspecting type hints, class types, and run-time types generically.

Based on:
  https://github.com/ilevkivskyi/typing_inspect/tree/master (MIT License)
  https://github.com/lebrice/SimpleParsing/blob/master/simple_parsing/utils.py (MIT License)

Cleaned up for python 3.10+ only.
"""

import builtins
import collections.abc
import dataclasses
import inspect
import types
import typing
from enum import Enum
from typing import (
    Any,
    Container,
    Dict,
    ForwardRef,
    List,
    Mapping,
    MutableMapping,
    Sequence,
    Set,
    Tuple,
    TypeGuard,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from haven.types import Dataclass

T = TypeVar("T")

builtin_types = [
    getattr(builtins, d) for d in dir(builtins) if isinstance(getattr(builtins, d), type)
]


def is_typevar(t) -> bool:
    return type(t) is TypeVar


def get_bound(t):
    if is_typevar(t):
        return getattr(t, "__bound__", None)
    else:
        raise TypeError(f"type is not a `TypeVar`: {t}")


def is_forward_ref(t) -> TypeGuard[typing.ForwardRef]:
    return isinstance(t, typing.ForwardRef)


def get_forward_arg(fr: ForwardRef) -> str:
    return getattr(fr, "__forward_arg__")


def is_dataclass_instance(obj: Any) -> TypeGuard[Dataclass]:
    return dataclasses.is_dataclass(obj) and dataclasses.is_dataclass(type(obj))


def is_dataclass_type(obj: Any) -> TypeGuard[type[Dataclass]]:
    return inspect.isclass(obj) and dataclasses.is_dataclass(obj)


def get_container_item_type(container_type: type[Container[T]]) -> Any:
    """Returns the `type` of the items in the provided container `type`.

    When no type annotation is found, or no item type is found, returns
    `typing.Any`.
    NOTE: If a type with multiple arguments is passed, only the first type
    argument is returned.

    >>> import typing
    >>> from typing import List, Tuple
    >>> get_container_item_type(list)
    typing.Any
    >>> get_container_item_type(List)
    typing.Any
    >>> get_container_item_type(tuple)
    typing.Any
    >>> get_container_item_type(Tuple)
    typing.Any
    >>> get_container_item_type(List[int])
    <class 'int'>
    >>> get_container_item_type(List[str])
    <class 'str'>
    >>> get_container_item_type(List[float])
    <class 'float'>
    >>> get_container_item_type(List[float])
    <class 'float'>
    >>> get_container_item_type(List[Tuple])
    typing.Tuple
    >>> get_container_item_type(List[Tuple[int, int]])
    typing.Tuple[int, int]
    >>> get_container_item_type(Tuple[int, str])
    <class 'int'>
    >>> get_container_item_type(Tuple[str, int])
    <class 'str'>
    >>> get_container_item_type(Tuple[str, str, str, str])
    <class 'str'>

    Arguments:
        list_type {Type} -- A type, preferably one from the Typing module (List, Tuple, etc).

    Returns:
        Type -- the type of the container's items, if found, else Any.
    """
    if container_type in {
        list,
        set,
        tuple,
        List,
        Set,
        Tuple,
        Dict,
        Mapping,
        MutableMapping,
    }:
        # the built-in `list` and `tuple` types don't have annotations for their item types.
        return Any
    type_arguments = getattr(container_type, "__args__", None)
    if type_arguments:
        return type_arguments[0]
    else:
        return Any


def _mro(t: type) -> Sequence[type]:
    # TODO: This is mostly used in 'is_tuple' and such, and should be replaced with
    # either the built-in 'get_origin' from typing, or from typing-inspect.
    if t is None:
        return []
    if hasattr(t, "__mro__"):
        return t.__mro__
    elif get_origin(t) is type:
        return []
    elif hasattr(t, "mro") and callable(t.mro):
        return t.mro()
    return []


def is_list(t: type) -> bool:
    """returns True when `t` is a List type.

    Args:
        t (Type): a type.

    Returns:
        bool: True if `t` is list or a subclass of list.

    >>> from typing import *
    >>> is_list(list)
    True
    >>> is_list(tuple)
    False
    >>> is_list(List)
    True
    >>> is_list(List[int])
    True
    >>> is_list(List[Tuple[int, str, None]])
    True
    >>> is_list(Optional[List[int]])
    False
    >>> class foo(List[int]):
    ...     pass
    >>> is_list(foo)
    True
    """
    return list in _mro(t)


def is_tuple(t: type) -> bool:
    """returns True when `t` is a tuple type.

    Args:
        t (Type): a type.

    Returns:
        bool: True if `t` is tuple or a subclass of tuple.

    >>> from typing import *
    >>> is_tuple(list)
    False
    >>> is_tuple(tuple)
    True
    >>> is_tuple(Tuple)
    True
    >>> is_tuple(Tuple[int])
    True
    >>> is_tuple(Tuple[int, str, None])
    True
    >>> class foo(tuple):
    ...     pass
    >>> is_tuple(foo)
    True
    >>> is_tuple(List[int])
    False
    """
    return tuple in _mro(t)


def is_dict(t: type) -> bool:
    """returns True when `t` is a dict type or annotation.

    Args:
        t (Type): a type.

    Returns:
        bool: True if `t` is dict or a subclass of dict.

    >>> from typing import *
    >>> from collections import OrderedDict
    >>> is_dict(dict)
    True
    >>> is_dict(OrderedDict)
    True
    >>> is_dict(tuple)
    False
    >>> is_dict(Dict)
    True
    >>> is_dict(Dict[int, float])
    True
    >>> is_dict(Dict[Any, Dict])
    True
    >>> is_dict(Optional[Dict])
    False
    >>> is_dict(Mapping[str, int])
    True
    >>> class foo(Dict):
    ...     pass
    >>> is_dict(foo)
    True
    """
    mro = _mro(t)
    return dict in mro or Mapping in mro or collections.abc.Mapping in mro


def is_set(t: type) -> bool:
    """returns True when `t` is a set type or annotation.

    Args:
        t (Type): a type.

    Returns:
        bool: True if `t` is set or a subclass of set.

    >>> from typing import *
    >>> is_set(set)
    True
    >>> is_set(Set)
    True
    >>> is_set(tuple)
    False
    >>> is_set(Dict)
    False
    >>> is_set(Set[int])
    True
    >>> is_set(Set["something"])
    True
    >>> is_set(Optional[Set])
    False
    >>> class foo(Set):
    ...     pass
    >>> is_set(foo)
    True
    """
    return set in _mro(t)


def is_dataclass_type_or_typevar(t: type) -> bool:
    """Returns whether t is a dataclass type or a TypeVar of a dataclass type.

    Args:
        t (Type): Some type.

    Returns:
        bool: Whether its a dataclass type.
    """
    return dataclasses.is_dataclass(t) or (is_typevar(t) and dataclasses.is_dataclass(get_bound(t)))


def is_enum(t: type) -> bool:
    if inspect.isclass(t):
        return issubclass(t, Enum)
    return Enum in _mro(t)


def is_bool(t: type) -> bool:
    return bool in _mro(t)


def is_tuple_or_list(t: type) -> bool:
    return is_list(t) or is_tuple(t)


def is_union(t: type) -> bool:
    """Returns whether or not the given Type annotation is a variant (or subclass) of typing.Union.

    Args:
        t (Type): some type annotation

    Returns:
        bool: Whether this type represents a Union type.

    >>> from typing import *
    >>> is_union(Union[int, str])
    True
    >>> is_union(Union[int, str, float])
    True
    >>> is_union(Tuple[int, str])
    False
    """
    if isinstance(t, types.UnionType):
        return True
    return getattr(t, "__origin__", "") == Union


def is_homogeneous_tuple_type(t: type[tuple]) -> bool:
    """Returns whether the given Tuple type is homogeneous: if all items types are the same.

    This also includes Tuple[<some_type>, ...]

    Returns
    -------
    bool

    >>> from typing import *
    >>> is_homogeneous_tuple_type(Tuple)
    True
    >>> is_homogeneous_tuple_type(Tuple[int, int])
    True
    >>> is_homogeneous_tuple_type(Tuple[int, str])
    False
    >>> is_homogeneous_tuple_type(Tuple[int, str, float])
    False
    >>> is_homogeneous_tuple_type(Tuple[int, ...])
    True
    >>> is_homogeneous_tuple_type(Tuple[Tuple[int, str], ...])
    True
    >>> is_homogeneous_tuple_type(Tuple[List[int], List[str]])
    False
    """
    if not is_tuple(t):
        return False
    type_arguments = get_type_arguments(t)
    if not type_arguments:
        return True
    assert isinstance(type_arguments, tuple), type_arguments
    if len(type_arguments) == 2 and type_arguments[1] is Ellipsis:
        return True
    # Tuple[str, str, str] -> True
    # Tuple[str, str, float] -> False
    # TODO: Not sure if this will work with more complex item times (like nested tuples)
    return len(set(type_arguments)) == 1


def is_optional(t: type) -> bool:
    """Returns True if the given Type is a variant of the Optional type.

    Parameters
    ----------
    - t : Type

        a Type annotation (or "live" type)

    Returns
    -------
    bool
        Whether or not this is an Optional.

    >>> from typing import Union, Optional, List
    >>> is_optional(str)
    False
    >>> is_optional(Optional[str])
    True
    >>> is_optional(Union[str, None])
    True
    >>> is_optional(Union[str, List])
    False
    >>> is_optional(Union[str, List, int, float, None])
    True
    """
    return is_union(t) and type(None) in get_type_arguments(t)


def is_tuple_or_list_of_dataclasses(t: type) -> bool:
    return is_tuple_or_list(t) and is_dataclass_type_or_typevar(get_container_item_type(t))


def get_type_arguments(container_type: type) -> tuple[type, ...]:
    return get_args(container_type)


def get_type_name(some_type: type):
    result = getattr(some_type, "__name__", str(some_type))
    type_arguments = get_type_arguments(some_type)
    if type_arguments:
        result += f"[{','.join(get_type_name(T) for T in type_arguments)}]"
    return result
