"""Utility functions used in various parts of the haven package."""

import collections.abc as c_abc
import copy
import dataclasses
import logging
from collections.abc import Iterable, Mapping, MutableMapping
from logging import getLogger
from typing import (
    Any,
    TypeVar,
)

from haven.type_inspector import is_dataclass_type
from haven.types import Dataclass

logger = getLogger(__name__)

T = TypeVar("T")


class HavenException(Exception):
    pass


class ParsingError(HavenException):
    pass


def keep_keys(d: dict, keys_to_keep: Iterable[str]) -> tuple[dict, dict]:
    d_keys = set(d.keys())  # save a copy since we will modify the dict.
    removed = {}
    for key in d_keys:
        if key not in keys_to_keep:
            removed[key] = d.pop(key)
    return d, removed


def flatten(d, parent_key=None, sep="."):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, c_abc.MutableMapping):
            items.extend(flatten(v, parent_key=new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def deflatten(d: dict[str, Any], sep: str = "."):
    deflat_d = {}
    for key in d:
        key_parts = key.split(sep)
        curr_d = deflat_d
        for inner_key in key_parts[:-1]:
            if inner_key not in curr_d:
                curr_d[inner_key] = {}
            curr_d = curr_d[inner_key]
        curr_d[key_parts[-1]] = d[key]
    return deflat_d


def remove_matching(dict_a, dict_b):
    dict_a = flatten(dict_a)
    dict_b = flatten(dict_b)
    for key in dict_b:
        if key in dict_a and dict_b[key] == dict_a[key]:
            del dict_a[key]
    return deflatten(dict_a)


def format_error(e: Exception):
    try:
        return f"{type(e).__name__}: {e}"
    except Exception:
        return f"Exception: {e}"


def import_object(path: str):
    import importlib

    parts = path.rsplit(".", 1)
    if len(parts) != 2:
        raise ImportError(
            f"Failed to import object from '{path}'. Should have at least one '.' separating module from object."
        )
    mod, attr = parts
    mod = importlib.import_module(mod)
    if not hasattr(mod, attr):
        raise ImportError(f"Module '{mod}' has no attribute '{attr}")
    return getattr(mod, attr)


def pytree_merge(dest: MutableMapping[Any, Any], src: Mapping[Any, Any]) -> None:
    for src_k, src_v in src.items():
        if src_k in dest and isinstance(src_v, Mapping) and isinstance(dest[src_k], MutableMapping):
            pytree_merge(dest[src_k], src_v)
        else:
            dest[src_k] = copy.deepcopy(src_v)


def get_defaults_dict(c: type[Dataclass]):
    """ " Get defaults of a dataclass without generating the object"""
    defaults_dict = {}
    for field in dataclasses.fields(c):
        if is_dataclass_type(field.type):
            defaults_dict[field.name] = get_defaults_dict(field.type)
        elif field.default is not dataclasses.MISSING:
            defaults_dict[field.name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            try:
                defaults_dict[field.name] = field.default_factory()
            except Exception as e:
                logging.debug(
                    f"Failed getting default for field {field.name} using its default factory.\n\tUnderlying error: {e}"
                )
                continue
    return defaults_dict
