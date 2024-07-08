from collections.abc import Callable
from typing import Any, Optional, TypeVar

from haven import formats
from haven.decoding import decode, type_decoders
from haven.encoding import encode
from haven.types import Dataclass, Pytree, ReadStream
from haven.utils import pytree_merge

TDataclass = TypeVar("TDataclass", bound=Dataclass)
T = TypeVar("T")


def load_pytree(cls: type[TDataclass], pytree: Pytree) -> TDataclass:
    """Decode a pytree into an instance of the given dataclass.

    Args:
        cls (type[TDataclass]): Dataclass to decode.
        pytree (Pytree): A tree of dicts and basic python objects matching the structure of `cls`.

    Returns:
        TDataclass: an instance of `cls` with values given by `pytree`.
    """
    return decode(cls, pytree)


def dump_pytree(obj: Dataclass) -> Pytree:
    """Encode a dataclass instance as a pytree

    Args:
        obj (Any): the datalass instance to convert.

    Returns:
        Pytree: a tree of basic python types matching the given dataclass.
    """
    return encode(obj)


def update(dc: TDataclass, overrides: Pytree) -> TDataclass:
    """Update a dataclass given overrides as a Pytree.

    Returns a copy and does not modify the original dataclass.

    Example:

      .. code-block:: python

        @dataclass
        Config:
            val: a = 5
            val2: b = 6

        cfg = haven.load_pytree(Config, {"a": 10})
        cfg = haven.update(cfg, {"b": 10})

        assert cfg.a == 10 and cf.b == 10

    Args:
        dc (TDataclass): Dataclass instance to update
        overrides (Pytree): Overrides as a pytree

    Returns:
        TDataclass: A new dataclass with overrides applied
    """
    pytree = encode(dc)
    pytree_merge(pytree, overrides)
    return decode(dc.__class__, pytree)


def update_from_dotlist(dc: TDataclass, dotlist: list[str]) -> TDataclass:
    """Update a dataclass instance with the overrides specified in the dotlist.

    Dotlists are lists of key=val strings. The keys can use dot syntax to reference
    fields deeper in the config tree. The values are parsed as yaml is. Example:

        .. code-block:: python
            update_from_dotlist(
                my_class, ["optim.lr=0.1", "model.arch=v5", "num_workers=6"]
            )

    This functionality is useful for providing command-line overrides. This function does
    not modify the original instance but instead returns a new copy.

    Args:
        dc (TDataclass): Dataclass instance to update.
        dotlist (list[str]): List of keyvalue strings.

    Returns
        TDataclass: the updated dataclass, as a copy.
    """
    pytree = formats.encode_dotlist(dotlist)
    return update(dc, pytree)


def add_encoder(ty: type[T], func: Callable[[T], Any]) -> Callable[[T], Any]:
    """Add function for converting instances of the given type to a pytree.

    Pytrees are composed of basic python builtin-types that are supported by
    YAML, JSON, and other similar formats.

    Args:
        ty (type[T]): the type to register
        func (Callable[[T], Any]): a function for encoding instances of the type T into a pytree.
    """
    encode.register(ty, func)
    return func


def add_decoder(
    ty: type[T], func: Callable[[Any], T], include_subclasses: bool = False
) -> Callable[[Any], T]:
    """Add a function for converting pytrees to instances of the given type.

    Pytrees are composed of basic python builtin-types that are supported by
    YAML, JSON, and other similar formats.

    Args:
        ty (type[T]): the type to register
        func (Callable[[Any], T]): a function that decodes pytrees into instances of T.
        include_subclasses (bool, optional): Whether to also apply this decoder for all subclasses of T. Defaults to False.
    """
    type_decoders.register(ty, func, include_subclasses)
    return func


def load(
    cls: type[TDataclass],
    stream: ReadStream,
    format: str = "yaml",
    overrides: Optional[Pytree] = None,
    dotlist_overrides: Optional[list[str]] = None,
) -> TDataclass:
    """Parse a text-based markup format and load it into an instance of the given dataclass

    Supported formats:
     - "yaml"
     - "json"

    Args:
        cls (type[TDataclass]): A dataclass to instantiate
        stream (ReadStream): A string or file-like object to read
        format (str, optional): The format to expect. Defaults to "yaml".
        overrides (Pytree, optional): A pytree of values to override the values from the stream.
        dotlist_overrides(list[str], optional): A list of overrides in "dotlist format", e.g.
            `["model.num_layers=5", "optim.lr=1e-3", "something.sizes=[1,2,3]"]`. Useful in
            combination with argparse.REMAINDER to provide CLI config setting.

    Raises:
        ValueError: If an unknown format is specified.

    Returns:
        TDataclass: An instance of the given dataclass with values taken from the text document.
    """
    if format == "yaml":
        pytree = formats.encode_yaml(stream)
    elif format == "json":
        pytree = formats.encode_json(stream)
    else:
        raise ValueError(f"Invalid format '{format}'. Expected one of yaml, json.")

    if overrides is not None:
        pytree_merge(pytree, overrides)

    if dotlist_overrides is not None:
        dotlist_pytree = formats.encode_dotlist(dotlist_overrides)
        pytree_merge(pytree, dotlist_pytree)

    return decode(cls, pytree)


def dump(obj: Dataclass, format: str = "yaml") -> str:
    """Convert an instance of a dataclass

    See :meth:`load` for a list of supported formats.

    Args:
        obj (Dataclass): the object to encode.
        format (str, optional): the format to output. Defaults to "yaml".

    Raises:
        ValueError: If an unknown format is specified.

    Returns:
        str: a text representation of the dataclass in the specified format.
    """
    pytree = encode(obj)
    if format == "yaml":
        return formats.decode_yaml(pytree)
    elif format == "json":
        return formats.decode_json(pytree)
    else:
        raise ValueError("Invalid format '{format}'. Expeceted one of yaml, json.")
