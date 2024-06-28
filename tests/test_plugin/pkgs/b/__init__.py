from dataclasses import dataclass

from tests.test_pkg.base import Base


@dataclass
class Test1(Base):
    b: int = 3


@dataclass
class Test2(Base):
    c: int = 8


def run1(cfg: Test1) -> int:
    return cfg.b


def run2(cfg: Test2) -> int:
    return cfg.c


tasks = [run1, run2]
