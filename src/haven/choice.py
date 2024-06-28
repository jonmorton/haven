import abc
import importlib
import pkgutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import cache
from inspect import isclass, isfunction
from typing import Any, Optional, TypeAlias, TypeVar

from haven.type_inspector import is_dataclass_type
from haven.types import Dataclass
from haven.utils import ParsingError, format_error, import_object

T = TypeVar("T")
TDataclass = TypeVar("TDataclass", bound=Dataclass)
ChoiceType: TypeAlias = str | Callable[..., Any] | type[Dataclass]


def try_import(spec: str):
    try:
        cls: type[Dataclass] = import_object(spec)
    except Exception as e:
        raise ParsingError(
            f"Could not import choice at '{spec}'.\nUnderlying error: {format_error(e)}"
        )
    return cls


class ChoiceProvider(abc.ABC):
    @abc.abstractmethod
    def get_choices(self) -> dict[str, str | type[Dataclass]]: ...

    def get_value(self, choice_name: str) -> Optional[type[Dataclass]]:
        choices = self.get_choices()
        if choice_name not in choices:
            return None
        choice = choices[choice_name]
        if isinstance(choice, str):
            return try_import(choice)
        else:
            return choice

    def get_choice_names(self) -> Iterable[str]:
        return self.get_choices().keys()


class DictProvider(ChoiceProvider):
    def __init__(self, choices: dict[str, ChoiceType]):
        self.choices = choices

    def get_choices(self):
        return self.choices


def parse_choices(
    choices: list[ChoiceType] | dict[str, ChoiceType] | ChoiceProvider,
) -> ChoiceProvider:
    if isinstance(choices, (list, tuple)):
        return iterable_provider(choices)
    elif isinstance(choices, dict):
        return DictProvider(choices)
    elif isinstance(choices, ChoiceProvider):
        return choices
    else:
        raise TypeError("Choices must be list, dict, or ChoiceProvider.")


class Plugin(ChoiceProvider):
    def __init__(self, discover_packages_path: str, attr: str):
        self.discover_packages_path = discover_packages_path
        self.attr = attr

    @cache
    def get_choices(self) -> dict[str, str]:
        package_module = importlib.import_module(self.discover_packages_path, __package__)

        choices = {}
        for mod_info in pkgutil.iter_modules(package_module.__path__):
            module = importlib.import_module(f"{self.discover_packages_path}.{mod_info.name}")
            if hasattr(module, self.attr):
                val = getattr(module, self.attr)
                print(val)
                if isinstance(val, (list, dict, ChoiceProvider)):
                    for k, v in parse_choices(val).get_choices().items():
                        print(k, v)
                        if k in choices:
                            raise ParsingError(
                                f"Duplicate choices registered for '{k}' in plugin provider."
                            )
                        choices[k] = v
                else:
                    choices[mod_info.name] = val

        return choices


def iterable_provider(choices: Iterable[ChoiceType]) -> ChoiceProvider:
    choice_dict = {}
    for c in choices:
        if isinstance(c, str):
            parts = c.rsplit(".", 1)
            if len(parts) != 2:
                raise ValueError(
                    f"Choice strings must be valid object import path (e.g. module.MyClass) Got: '{c}'"
                )
            choice_dict[parts[-1]] = c
        elif isfunction(c) or is_dataclass_type(c) or isclass(c):
            choice_dict[c.__name__] = c
        else:
            raise TypeError(f"Objects passed as choices must be dataclasses. Got: '{c}'")

    return DictProvider(choice_dict)


@dataclass
class ChoiceMeta:
    choices: ChoiceProvider
    key_field: str = "name"
    outer: bool = False


def choice(
    choices: list[ChoiceType] | dict[str, ChoiceType] | ChoiceProvider,
    key_field: str = "name",
    outer: bool = False,
    default_factory: Callable[[], T] | str | None = None,
) -> T:
    """Dynamically selects dataclasses to decode based on the value of another string field.

    Choice types construct a name, dataclass mapping. During config parsing, the value of another
    field in the child or parent dataclass is used to lookup which dataclass to decode.

    The `choices` argument can be either a list or dict; if it is a list, then the name for each choice
    is determined automatically by inspecting the name of the class or function. The list/dict values
    can either contain the choices directly or strings of the form `my_package.my_module.MyClass`.

    Note:
        The `default_factory` argument works as expected in standard dataclass construction, but when constructed
        via this library the value of the key field will always override it, since it controls which choice to use.

    Args:
        choices (list[str  |  type[Dataclass]] | dict[str, str  |  type[Dataclass]] ): a list or dict of possible choices.
        key_field (str, optional): the name of the field which determines the choice at runtime. Defaults to "name".
        outer (bool, optional): If true, the choice field is a sibling in the parent dataclass. If false, it is a
            member of this field's dataclass. Defaults to False.
        default_factory (Callable[..., TDataclass] | str, optional): If str, import the object specified and use that class as the
            default factory. Otherwise, a callable that returns a dataclass instance or None for no default.

    Raises:
        ValueError: raised if import strings don't follow the correct format.
        TypeError: raised if the passed objects are not dataclasses or if `choices` is not a dict or list.
    """
    provider = parse_choices(choices)

    metadata = {
        "_haven_choices": ChoiceMeta(
            choices=provider,
            key_field=key_field,
            outer=outer,
        ),
    }

    kwargs = {}
    if isinstance(default_factory, str):
        kwargs["default_factory"] = import_object(default_factory)
    elif default_factory is not None:
        kwargs["default_factory"] = default_factory

    return field(metadata=metadata, **kwargs)


def plugin(
    discover_packages_path: str,
    attr: str,
    key_field: str = "name",
    outer: bool = False,
    default_factory: Callable[[], T] | str | None = None,
):
    """Discover choices as all modules in a package namespace automatically.

    Similar to the :meth:`choices` function, but it doesn't require explicitly
    specifying all available choices upfront. Instead, all submodules of the given
    package are discovered at decoding time as available choices. The module
    attribute specified by `attr` is used as the factory choice. In most cases it
    should simply be a dataclass.

    The choice name is the same as the module name.

    Args:
        discover_packages_path (str): the namespace in which to discover packages
        attr (str): the attribute expected in each module to use as the choice value
        key_field (str, optional): The field use to determine the choice. Defaults to "name".
            Same function as in :meth:`choice`
        outer (bool, optional): Same as in :meth:`choice`. Defaults to False.
        default_factory (Callable[..., TDataclass] | str | None, optional): Defaults to None.
    """
    return choice(
        Plugin(discover_packages_path, attr),
        key_field,
        outer=outer,
        default_factory=default_factory,
    )
