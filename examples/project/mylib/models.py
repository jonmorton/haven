from dataclasses import dataclass

from mylib.config import Model, ModelConfig


@dataclass
class GPTConfig(ModelConfig):
    embed_dim: int = 512
    seq_len: int = 512
    head_dim: int = 64


class GPT(Model):
    def __init__(self, cfg: GPTConfig):
        self.seq_len = cfg.seq_len

    def __repr__(self):
        return f"<GPT seq_len={self.seq_len}>"


@dataclass
class MambaConfig(ModelConfig):
    hdim: int = 512
    nblock: int = 10


class Mamba(Model):
    def __init__(self, cfg: MambaConfig):
        self.num_blocks = cfg.nblock

    def __repr__(self):
        return f"<Mamba nblock={self.num_blocks}>"
