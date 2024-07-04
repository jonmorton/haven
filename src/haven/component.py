import abc
import inspect
from typing import Callable, Generic, ParamSpec, TypeVar, get_args, get_origin

from haven.type_inspector import is_dataclass_type
from haven.types import Dataclass
from haven.utils import ParsingError

TConf = TypeVar("TConf", bound=Dataclass, covariant=True)
TRet = TypeVar("TRet")

P = ParamSpec("P")


class Component(Generic[TConf, TRet]):
    """A simple wrapper that couples a config instance with a function or Class which
    accepts that config as the first argument.
    """

    def __init__(self, config: TConf, func: Callable[..., TRet]):
        self.config = config
        self.func = func

    def __call__(self, *args, **kwargs) -> TRet:
        """Call the underlying function with the config dataclass as the first argument.
        All other args are forwarded."""
        return self.func(self.config, *args, **kwargs)


class ComponentBuilder(abc.ABC):
    @abc.abstractmethod
    def get_dataclass(self) -> type[Dataclass]: ...

    @abc.abstractmethod
    def build(self, conf: Dataclass) -> Component: ...


def get_component_dataclass(obj) -> type[Dataclass]:
    if is_dataclass_type(obj):
        return obj
    if isinstance(obj, ComponentBuilder):
        return obj.get_dataclass()
    arg_offset = 0
    if inspect.isclass(obj):
        obj = obj.__init__
        arg_offset = 1
    if inspect.isfunction(obj):
        params = list(inspect.signature(obj).parameters.values())
        if len(params) <= arg_offset:
            raise ParsingError(
                f"Choice function '{obj.__name__}' does not take any arguments, expeceted 1"
            )

        argdc = params[arg_offset].annotation
        if not is_dataclass_type(argdc):
            raise ParsingError(
                f"Choice function '{obj.__name__}' first argument's type is not a dataclass"
            )
        return argdc
    else:
        raise ValueError()


def get_component_type_dataclass(obj) -> type[Dataclass]:
    type_args = get_args(obj)
    if len(type_args) != 2:
        raise ParsingError("Component type should have two type args")
    return type_args[0]


def build_component(
    config: TConf, value: Callable[..., TRet] | ComponentBuilder
) -> Component[TConf, TRet]:
    if isinstance(value, ComponentBuilder):
        return value.build(config)
    return Component(config, value)


def is_component_type(ty) -> bool:
    orig = get_origin(ty)
    if orig is None:
        return False
    return issubclass(orig, Component)
