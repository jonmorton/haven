from dataclasses import dataclass

from mylib.config import Config, TaskConfig


@dataclass
class TrainConfig(TaskConfig):
    num_workers: int = 4


def run(train_cfg: TrainConfig, cfg: Config):
    print(f"Training with {train_cfg.num_workers} workers!")

    model = cfg.model()
    print(model)
