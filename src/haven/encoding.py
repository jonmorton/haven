"""Extensible dataclass to pytree encoding.

Use the external API function `add_encoder` to register encoders for new types.

import haven
import numpy as np
@haven.add_encoder
def encode_ndarray(obj: np.ndarray) -> str:
    return obj.tostring()
"""

from argparse import Namespace
from collections.abc import Hashable, Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from functools import singledispatch
from logging import getLogger
from os import PathLike
from typing import Any

from haven.component import Component
from haven.utils import ParsingError

logger = getLogger(__name__)


@singledispatch
def encode(obj: Any) -> Any:
    """Encodes an object into a json/yaml-compatible primitive type."""
    if is_dataclass(obj):
        d: dict[str, Any] = dict()
        for field in fields(obj):
            value = getattr(obj, field.name)
            try:
                d[field.name] = encode(value)
            except TypeError as e:
                raise ParsingError(f"Unable to encode field {field.name}") from e
        return d
    elif obj is None:
        return None
    else:
        raise ParsingError(
            f"No parser for object {obj} of type {type(obj)}, consider using haven.encode.register"
        )


@encode.register(Mapping)
def encode_dict(obj: Mapping) -> dict[Any, Any] | list[tuple[Any, Any]]:
    result = {}
    for k, v in obj.items():
        k_ = encode(k)
        v_ = encode(v)
        if isinstance(k_, Hashable):
            result[k_] = v_
        else:
            return [(encode(x), encode(y)) for x, y in obj.items()]
    return result


@encode.register(Enum)
def encode_enum(obj: Enum) -> str:
    return obj.name


@encode.register(Component)
def encode_component(obj: Component) -> dict[str, Any]:
    return encode(obj.config)


for t in [str, float, int, bool, bytes]:
    encode.register(t, lambda x: x)

for t in [list, tuple, set]:
    encode.register(t, lambda x: list(map(encode, x)))

encode.register(PathLike, lambda x: x.__fspath__())

encode.register(Namespace, lambda x: encode(vars(x)))
