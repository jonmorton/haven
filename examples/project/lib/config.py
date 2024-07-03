from dataclasses import dataclass

import haven


@dataclass
class TaskConfig:
    def run(self):
        pass


class Model:
    pass


@dataclass
class ModelConfig:
    name: str

    def build(self):
        pass


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
        discover_packages_path="lib.tasks",
        attr="run",
        key_field="task_name",
        outer=True,
    )
    model: haven.Component[ModelConfig, Model] = haven.choice(
        ["lib.models.GPT", "lib.models.Mamba"], "name"
    )
    out_dir: str = "./output"
