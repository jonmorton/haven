from mylib.config import GPTConfig, MambaConfig, Model


class GPT(Model):
    def __init__(self, cfg: GPTConfig):
        self.seq_len = cfg.seq_len

    def __repr__(self):
        return f"<GPT seq_len={self.seq_len}>"


class Mamba(Model):
    def __init__(self, cfg: MambaConfig):
        self.num_blocks = cfg.nblock

    def __repr__(self):
        return f"<Mamba nblock={self.num_blocks}>"
