from dataclasses import dataclass

from .base import Base


@dataclass
class Test(Base):
    b: int = 5


def run(cfg: Test) -> int:
    return cfg.b
