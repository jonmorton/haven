from dataclasses import dataclass

import haven


@dataclass
class TaskConfig:
    name: str


class Model:
    pass


@dataclass
class ModelConfig:
    name: str


@dataclass
class Config:
    task: haven.Component[TaskConfig, None] = haven.plugin(
        discover_packages_path="mylib.tasks",
        attr="run",
    )
    model: haven.Component[ModelConfig, Model] = haven.choice(
        ["mylib.models.GPT", "mylib.models.Mamba"],
    )
    out_dir: str = "./output"
