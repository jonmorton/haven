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
class GPTConfig(ModelConfig):
    embed_dim: int = 512
    seq_len: int = 512
    head_dim: int = 64


@dataclass
class MambaConfig(ModelConfig):
    hdim: int = 512
    nblock: int = 10


@dataclass
class Config:
    task_name: str
    task: haven.Component[TaskConfig, None] = haven.plugin(
        discover_packages_path="mylib.tasks",
        attr="run",
    )
    model: haven.Component[ModelConfig, Model] = haven.choice(
        ["mylib.models.GPT", "mylib.models.Mamba"],
    )
    out_dir: str = "./output"
