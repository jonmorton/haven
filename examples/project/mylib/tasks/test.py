from dataclasses import dataclass

from mylib.config import TaskConfig


@dataclass
class Test(TaskConfig):
    metric: str


def run(cfg: Test):
    print(f"Calculating the '{cfg.metric}' metric")
