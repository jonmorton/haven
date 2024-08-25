"""Functions for decoding dataclass fields from "raw" values (e.g. from json)."""

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import MISSING, Field, fields, is_dataclass
from functools import lru_cache, partial
from logging import getLogger
from pathlib import Path
from typing import (
    Any,
    Optional,
    TypeVar,
)

from haven.choice import ChoiceMeta
from haven.component import (
    build_component,
    get_component_dataclass,
    get_component_type_dataclass,
    is_component_type,
)
from haven.type_inspector import (
    get_bound,
    get_type_arguments,
    is_dataclass_type,
    is_dict,
    is_enum,
    is_list,
    is_set,
    is_tuple,
    is_typevar,
    is_union,
)
from haven.type_registry import RegistryFunc, TypeRegistry
from haven.types import Dataclass
from haven.utils import (
    ParsingError,
    format_error,
)

logger = getLogger(__name__)
T = TypeVar("T", bound=Dataclass)
K = TypeVar("K")
V = TypeVar("V")


type_decoders = TypeRegistry()


def decode(cls: type[T], raw_value: Any) -> T:
    return get_decoding_fn(cls)(raw_value)


@lru_cache(maxsize=128)
def get_decoding_fn(cls: type[T]) -> Callable[[Any], T]:
    """Fetches/Creates a decoding function for the given type annotation.

    This decoding function can then be used to create an instance of the type
    when deserializing dicts.
    """
    # Start by trying the dispatch mechanism
    registered_func: Optional[RegistryFunc] = type_decoders.dispatch(cls)
    if registered_func is not None:
        # If supports subclasses, pass the actual type
        if registered_func.include_subclasses:
            return partial(registered_func.func, cls)
        else:
            return registered_func.func

    if is_dataclass_type(cls):
        return partial(decode_dataclass, cls)  # type: ignore

    if cls is Any:
        logger.debug(f"Decoding an Any type: {cls}")
        return no_op

    if is_dict(cls):
        logger.debug(f"Decoding a Dict field: {cls}")
        args = get_type_arguments(cls)
        if args is None or len(args) != 2:
            args = (Any, Any)
        return decode_dict(*args)  # type: ignore

    if is_set(cls):
        logger.debug(f"Decoding a Set field: {cls}")
        args = get_type_arguments(cls)
        if args is None or len(args) != 1:
            args = (Any,)
        return decode_set(args[0])  # type: ignore

    if is_tuple(cls):
        logger.debug(f"Decoding a Tuple field: {cls}")
        args = get_type_arguments(cls)
        if args is None:
            args = []
        return decode_tuple(*args)  # type: ignore

    if is_list(cls):  # NOTE: Looks like can't be written with a dictionary
        logger.debug(f"Decoding a List field: {cls}")
        args = get_type_arguments(cls)
        if args is None or len(args) != 1:
            # Using a `List` or `list` annotation, so we don't know what do decode the
            # items into!
            args = (Any,)
        decode_fn = decode_list(args[0])  # type: ignore

        return decode_fn  # type: ignore

    if is_union(cls):
        logger.debug(f"Decoding a Union field: {cls}")
        args = get_type_arguments(cls)
        return decode_union(*args)

    if is_enum(cls):
        return lambda key: cls[key]  # type: ignore

    if is_typevar(cls):
        bound = get_bound(cls)
        logger.debug(f"Decoding a typevar: {cls}, bound type is {bound}.")
        if bound is not None:
            return get_decoding_fn(bound)

    raise ParsingError(f"No decoding function for type {cls}, consider using haven.decode.register")


def decode_dataclass(cls: type[Dataclass], d: dict[str, Any]) -> Dataclass:
    """Parses an instance of the dataclass `cls` from the dict `d`."""
    obj_dict: dict[str, Any] = d.copy()

    init_args: dict[str, Any] = {}
    non_init_args: dict[str, Any] = {}

    logger.debug(f"from_dict for {cls}")

    for field in fields(cls):
        name = field.name

        if "_haven_choices" in field.metadata:
            raw_value = obj_dict.pop(name, {})
            field_value = decode_choice_field(field, raw_value)
        elif name not in obj_dict:
            if field.default is MISSING and field.default_factory is MISSING:
                logger.warning(
                    f"Couldn't find the field '{name}' in the dict with keys " f"{list(d.keys())}"
                )
            continue
        else:
            raw_value = obj_dict.pop(name)
            try:
                field_value = decode_field(field, raw_value)
            except ParsingError as e:
                raise e
            except Exception as e:
                raise ParsingError(
                    f'Failed when parsing value=\'{raw_value}\' into field "{cls}.{name}" of type {field.type}.\n\tUnderlying error is "{format_error(e)}"'
                )

        if field.init:
            init_args[name] = field_value
        else:
            non_init_args[name] = field_value

    extra_args = obj_dict

    # If there are arguments left over in the dict after taking all fields.
    if extra_args:
        raise Exception(f"The fields {extra_args} do not belong to the class")

    init_args.update(extra_args)
    try:
        instance = cls(**init_args)  # type: ignore
    except TypeError as e:
        raise ParsingError(
            f"Couldn't instantiate class {cls} using the given arguments.\n\t Underlying error: {e}"
        )

    for name, value in non_init_args.items():
        logger.debug(f"Setting non-init field '{name}' on the instance.")
        setattr(instance, name, value)
    return instance


def decode_field(field: Field, raw_value: Any) -> Any:
    """Converts a "raw" value (e.g. from json file) to the type of the `field`."""
    name = field.name
    field_type = field.type
    logger.debug(f"Decode name = {name}, type = {field_type}")
    return decode(field_type, raw_value)


def decode_choice_field(field: Field, raw_value: Any) -> Any:
    meta: ChoiceMeta = field.metadata["_haven_choices"]

    if not isinstance(raw_value, dict):
        raise ParsingError(
            f"Choice field '{field.name}' only works for dataclasses, expected dict when decoding"
        )

    targ_dict = raw_value
    choice_name = None

    if meta.key_field not in targ_dict:
        # Key field name not found in the dict, find the default value from the field definition
        targ_cls = field.type
        if is_component_type(targ_cls):
            targ_cls = get_component_type_dataclass(targ_cls)
        if not is_dataclass(targ_cls):
            raise ParsingError("The choice field type is not a dataclass.")
        for f in fields(targ_cls):
            if f.name == meta.key_field:
                if f.default is not MISSING:
                    choice_name = f.default
                elif f.default_factory is not MISSING:
                    choice_name = f.default_factory()

        if choice_name is None:
            raise ParsingError(
                f"Choice field '{field.name}' cannot find key field '{meta.key_field}' for determining which choice to use, and no default value was found."
            )
    else:
        choice_name = targ_dict[meta.key_field]

        if not isinstance(choice_name, str):
            raise ParsingError(f"Choice field '{field.name}' has '{meta.key_field}")

    choice = meta.choices.get_value(choice_name)

    if choice is None:
        raise ParsingError(
            f"Invalid choice '{choice_name}' for field '{field.name}'. Valid choices are: {','.join(meta.choices.get_choice_names())}"
        )

    cls = get_component_dataclass(choice)
    conf = decode_dataclass(cls, raw_value)

    if is_component_type(field.type):
        return build_component(conf, choice)
    elif is_dataclass_type(field.type):
        return conf
    else:
        raise ParsingError()


def decode_optional(t: type[T]) -> Callable[[Any | None], T | None]:
    decode = get_decoding_fn(t)

    def _decode_optional(val: Any | None) -> T | None:
        return val if val is None else decode(val)

    return _decode_optional


def try_functions(*funcs: Callable[[Any], T]) -> Callable[[Any], T | Any]:
    """Tries to use the functions in succession, else returns the same value unchanged."""

    def _try_functions(val: Any) -> T | Any:
        for func in funcs:
            try:
                return func(val)
            except Exception:
                continue
        # If no function worked, raise an exception
        raise ParsingError(f"No valid parsing for value {val}")

    return _try_functions


def decode_union(*types: type) -> Callable[[Any], Any]:
    types: list[type[Any]] = list(types)
    optional = type(None) in types
    # Partition the Union into None and non-None types.
    while type(None) in types:
        types.remove(type(None))

    decoding_fns: list[Callable[[Any], Any]] = [
        decode_optional(t) if optional else get_decoding_fn(t)  # type: ignore
        for t in types
    ]  # type: ignore
    # Try using each of the non-None types, in succession. Worst case, return the value.
    return try_functions(*decoding_fns)


def decode_list(t: type[T]) -> Callable[[list[Any]], list[T]]:
    decode_item = get_decoding_fn(t)

    def _decode_list(val: list[Any]) -> list[T]:
        # assert type(val) == list
        if not isinstance(val, list):
            raise ParsingError(f"The given value='{val}' is not of a valid input")
        return [decode_item(v) for v in val]

    return _decode_list


def decode_tuple(*tuple_item_types: type[T]) -> Callable[[list[T]], tuple[T, ...]]:
    """Makes a parsing function for creating tuples."""
    # Get the decoding function for each item type
    has_ellipsis = False
    if Ellipsis in tuple_item_types:
        # TODO: This isn't necessary, the ellipsis will always be at index 1.
        ellipsis_index = tuple_item_types.index(Ellipsis)
        decoding_fn_index = ellipsis_index - 1
        decoding_fn = get_decoding_fn(tuple_item_types[decoding_fn_index])
        has_ellipsis = True
    elif len(tuple_item_types) == 0:
        has_ellipsis = True
        decoding_fn = no_op  # Functionality will be the same as Tuple[Any,...]
    else:
        decoding_fns = [get_decoding_fn(t) for t in tuple_item_types]

    # Note, if there are more values than types in the tuple type, then the
    # last type is used.

    def _decode_tuple(val: list[T]) -> tuple[T, ...]:
        if val is None:
            raise TypeError("Value must not be None for conversion to a tuple")
        if has_ellipsis:
            return tuple(decoding_fn(v) for v in val)
        else:
            if len(decoding_fns) != len(val):
                err_msg = (
                    f"Trying to decode {len(val)} values for a predfined {len(decoding_fns)}-Tuple"
                )
                raise ParsingError(err_msg)
            return tuple(decoding_fns[i](v) for i, v in enumerate(val))

    return _decode_tuple


def decode_set(item_type: type[T]) -> Callable[[list[T]], set[T]]:
    """Makes a parsing function for creating sets with items of type `item_type`."""
    # Get the parsers fn for a list of items of type `item_type`.
    parse_list_fn = decode_list(item_type)

    def _decode_set(val: list[Any]) -> set[T]:
        return set(parse_list_fn(val))

    return _decode_set


def decode_dict(K_: type[K], V_: type[V]) -> Callable[[list[tuple[Any, Any]]], dict[K, V]]:
    """Creates a decoding function for a dict type. Works with OrderedDict too."""
    decode_k = get_decoding_fn(K_)
    decode_v = get_decoding_fn(V_)

    def _decode_dict(val: dict[Any, Any] | list[tuple[Any, Any]]) -> dict[K, V]:
        result: dict[K, V] = {}
        if isinstance(val, list):
            result = OrderedDict()
            items = val
        elif isinstance(val, OrderedDict):
            # NOTE: Needed to propagate `OrderedDict` type
            result = OrderedDict()
            items = val.items()
        else:
            items = val.items()
        for k, v in items:
            k_ = decode_k(k)
            v_ = decode_v(v)
            result[k_] = v_
        return result

    return _decode_dict


def no_op(v: T) -> T:
    """Decoding function that gives back the value as-is."""
    return v


def try_constructor(t: type[T]) -> Callable[[Any], T | Any]:
    """Tries to use the type as a constructor. If that fails, returns the value as-is."""
    return try_functions(lambda val: t(**val), lambda val: t(val))  # type: ignore


# Dictionary mapping from types/type annotations to their decoding functions.
for t in [str, float, int, bool, bytes]:
    type_decoders.register(t, t)

type_decoders.register(Path, Path)
