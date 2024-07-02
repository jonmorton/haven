<h1 align="center">haven</p>

<p align="center">
    <a href="https://badge.fury.io/py/haven-conf"><img src="https://badge.fury.io/py/haven-conf.svg" alt="PyPI version" height="18"></a>
    <a href="https://github.com/jonmorton/haven/actions/workflows/pytest.yml"><img src="https://github.com/jonmorton/haven/workflows/pytest.yml/badge.svg" alt="PyTest" height="18"></a>
    <a href="#contributors-"><img src="https://img.shields.io/badge/all_contributors-2-orange.svg" alt="All Contributors" height="18"></a>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" height="18"></a>
</p>

## A modular dataclass configuration system

`Haven` is system for configuring applications using dataclasses and YAML. It strives to be relatively simple while still scaling to complex use cases.

## Key Features

 * Builds plain dataclasses, so you can use all standard dataclass features, such as custom methods, `__post_init__`, etc.
 * Doesn't take over your CLI or impose certain structure on your program.
 * Support for parsing a wide variety of types and type hints, including optionals and unions.
 * Scales to projects with many config variations or sub-components using `choice` and `plugin` fields.
 * Easily link each config variation to the matching variation of your code using `Component`.


## Tour

### Basic example

```python
@dataclass
class ModelConfig:
    num_layers: int = 5
    embed_dim: int = 512

@dataclass
class TrainConfig:
    workers: int = 5
    steps: list[int] = field(default_factory=lambda: [50, 100 150])
    model: ModelConfig = field(default_factory=ModelConfig)

# Load from yaml string
cfg = haven.load(TrainConfig, """
steps: [1,2,3]
model:
  num_layers: 16
""")
assert cfg.model.num_layers == 16

# Or load from file
with open("config.yaml") as f:
    cfg = haven.load(TrainConfig, f)

# Update using "dotlist" style overrides (e.g. from CLI args)
cfg = haven.update_from_dotlist(cfg, ["workers=3", "model.num_layers=2"])

# Print yaml
print(haven.dump(cfg))
```


### Choice fields

More complex projects often want to support many variations for each application component. This can be accomplished through subclassing and choice fields.

```python
@dataclass
class ModelConfig:
    name: str

# Two types of models
@dataclass
class GPT2Config(ModelConfig):
    num_layers: int

@dataclass
class Llama2Config(ModelConfig):
    embed_dim: int = 512

@dataclass
class TrainConfig:
    workers: int = 5
    steps: list[int] = field(default_factory=lambda: [50, 100 150])

    # Choose config class based on value of `ModelConfig.name`.
    model: ModelConfig = haven.choice(
        [GPT2Config, Llama2Config],
        key_field="name",
        default_factory=Llama2Config,
    )

# Load from yaml string
cfg = haven.load(TrainConfig, """
steps: [1,2,3]
model:
  name: GPT2Config
  num_layers: 16
""")
assert isinstance(cfg.model, GPT2Config)
```

Chocies can also be module + object paths that are imported lazily:

```python
@dataclass
class TrainConfig:
    model: ModelConfig = haven.choice([
        "models.llama.Llama2Config",
        "models.gpt.GPT2Config",
    ])
```

The benefit of this style of configuration is that all of the available choices are documented directly in the config  definition. This works well when there are a small to medium number of variations. For more flexibility,
a plugin system is available:

```python
@dataclass
class TrainConfig:
    model: ModelConfig = haven.plugin(
        discover_packages_path="mypackage.models",
        attr="MODEL_CONFIG",
    )
```

Each module under the `mypackage.models` namespace that contains the attribute `MODEL_CONFIG` will then be an available choice. The choice name is the same as the name of the module.

### Components

The problem with choice fields alone is that typically, you want to run different code in your application depending on which variant of the config was selected. `haven.Component` provides a simple mechanism for linking each variation to a callable.

```python
# Sample model definitions
class ModelBase(nn.Module):
    pass

class Llama2(Model):
    def __init__(self, cfg: Llama2Config):
        pass

class GPT(Model):
    def __init__(self, cfg: GPTConfig):
        pass

@dataclass
class TrainConfig:
    model: haven.Component[ModelConfig, ModelBase] = haven.choice([
        Llama2
        GPT,
    ])

cfg = haven.load(TrainConfig, "model: Llama2")

# Instantiate the chosen class, passing the appropriate config as the first arg.
model = cfg.model()
assert isinstance(model, Llama2)
```

The config dataclass to use for each variation is automatically derived from the type hint on the first argument of the callable.

### More examples

See the examples directory in the source code for more complete examples.

## API

See here.

