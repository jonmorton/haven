import string
import sys
from collections.abc import Callable
from contextlib import contextmanager, redirect_stderr
from io import StringIO
from typing import (
    Any,
    TypeVar,
)

import haven
import pytest
from haven.types import Dataclass
from haven.utils import ParsingError

xfail = pytest.mark.xfail
parametrize = pytest.mark.parametrize


def xfail_param(*args, reason: str):
    if len(args) == 1 and isinstance(args[0], tuple):
        args = args[0]
    return pytest.param(*args, marks=pytest.mark.xfail(reason=reason))


@contextmanager
def raises(
    exception: type[BaseException] = ParsingError,
    match=None,
    code: int | None = None,
):
    with pytest.raises(exception, match=match):
        yield


@contextmanager
def exits_and_writes_to_stderr(match: str = ""):
    s = StringIO()
    with redirect_stderr(s), raises(SystemExit):
        yield
    s.seek(0)
    err_string = s.read()
    if match:
        assert match in err_string, err_string
    else:
        assert err_string, err_string


@contextmanager
def raises_missing_required_arg():
    with exits_and_writes_to_stderr("the following arguments are required"):
        yield


@contextmanager
def raises_expected_n_args(n: int):
    with exits_and_writes_to_stderr(f"expected {n} arguments"):
        yield


@contextmanager
def raises_unrecognized_args(*args: str):
    with exits_and_writes_to_stderr("unrecognized arguments: " + " ".join(args or [])):
        yield


def assert_help_output_equals(actual: str, expected: str) -> None:
    # Replace the start with `prog`, since the tests runner might not always be
    # `pytest`, could also be __main__ when debugging with VSCode
    prog = sys.argv[0].split("/")[-1]
    if prog != "pytest":
        expected = expected.replace("usage: pytest", f"usage: {prog}")
    remove = string.punctuation + string.whitespace
    actual_str = "".join(actual.split())
    expected_str = "".join(expected.split())
    assert actual_str == expected_str, f"{actual_str} != {expected_str}"


T = TypeVar("T", bound=Dataclass)


class TestSetup:
    @classmethod
    def setup(
        cls: type[T],
        conf_yaml: str = "",
        overrides: list[str] = [],
    ) -> T:
        """Basic setup for a tests.

        Keyword Arguments:
            arguments {Optional[str]} -- The arguments to pass to the parser (default: {""})
            dest {Optional[str]} -- the attribute where the argument should be stored. (default: {None})

        Returns:
            {cls}} -- the class's type.
        """
        cfg = haven.load(cls, conf_yaml, format="yaml")
        if overrides:
            cfg = haven.update_from_dotlist(cfg, overrides)
        return cfg


ListFormattingFunction = Callable[[list[Any]], str]
ListOfListsFormattingFunction = Callable[[list[list[Any]]], str]


def format_list_using_spaces(value_list: list[Any]) -> str:
    return " ".join(str(p) for p in value_list)


def format_list_using_brackets(value_list: list[Any]) -> str:
    return f"[{','.join(str(p) for p in value_list)}]"


def format_list_using_single_quotes(value_list: list[Any]) -> str:
    return f"'{format_list_using_spaces(value_list)}'"


def format_list_using_double_quotes(value_list: list[Any]) -> str:
    return f'"{format_list_using_spaces(value_list)}"'


def format_lists_using_brackets(list_of_lists: list[list[Any]]) -> str:
    return " ".join(format_list_using_brackets(value_list) for value_list in list_of_lists)


def format_lists_using_double_quotes(list_of_lists: list[list[Any]]) -> str:
    return " ".join(format_list_using_double_quotes(value_list) for value_list in list_of_lists)


def format_lists_using_single_quotes(list_of_lists: list[list[Any]]) -> str:
    return " ".join(format_list_using_single_quotes(value_list) for value_list in list_of_lists)
