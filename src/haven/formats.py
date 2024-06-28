from typing import Any

from haven.types import Pytree, ReadStream
from haven.utils import deflatten


def encode_yaml(stream: ReadStream) -> Any:
    """
    Read yaml from a string or file-like object and encode it into a pytree.
    """
    if isinstance(stream, (str, bytes, bytearray)) and not stream:
        return {}

    import yaml

    return yaml.safe_load(stream)


def encode_json(stream: ReadStream) -> Any:
    """
    Read json from a string or file-like object and encode it into a pytree.
    """
    import json

    if isinstance(stream, (str, bytes, bytearray, memoryview)):
        if not stream:
            return {}
        return json.loads(stream)

    return json.load(stream)


def decode_yaml(obj: Any) -> str:
    """
    Convert a pytree into yaml string.
    """
    import yaml

    return yaml.dump(obj)


def decode_json(obj: Any) -> str:
    """
    Convert a pytree into a json string.
    """
    import json

    return json.dumps(obj)


def encode_dotlist(dotlist: list[str]) -> Pytree:
    """
    Parse a dotlist into a pytree.
    """
    kv = {}
    for arg in dotlist:
        idx = arg.find("=")
        if idx == -1:
            raise ValueError(f"dotlist argument '{arg}' invalid: no key.")
        if idx == len(arg) - 1:
            raise ValueError(f"dotlist argument '{arg}' invalid: no value given")
        if idx == 0:
            raise ValueError(f"dotlist argument '{arg} invalid: empty key")
        key = arg[0:idx]
        value = encode_yaml(arg[idx + 1 :])
        kv[key] = value

    return deflatten(kv)
