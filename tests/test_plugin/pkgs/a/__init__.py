from dataclasses import dataclass

from tests.test_pkg.base import Base


@dataclass
class Test(Base):
    a: int = 5


def run3(cfg: Test) -> int:
    return cfg.a


tasks = [run3]
