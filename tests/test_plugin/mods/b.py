from dataclasses import dataclass

from tests.test_pkg.base import Base


@dataclass
class Test(Base):
    b: int = 6


def run(cfg: Test) -> int:
    return cfg.b
