from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from _typeshed import DataclassInstance as _DataclassInstance
    from _typeshed import SupportsRead


Dataclass: TypeAlias = "_DataclassInstance"

# File-like types supported by config parser libraries like pyyaml.
ReadStream: TypeAlias = "str | bytes | SupportsRead[str] | SupportsRead[bytes]"

Pytree: TypeAlias = dict[str, Any]
