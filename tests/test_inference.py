import warnings
from types import SimpleNamespace

from transformers import GenerationConfig

from src.inference import deterministic_generation_config


def test_deterministic_generation_config_clears_sampling_warnings():
    source_config = GenerationConfig()
    source_config.do_sample = False
    source_config.temperature = 0
    source_config.top_p = 0.8
    source_config.top_k = 20
    model = SimpleNamespace(generation_config=source_config)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        config = deterministic_generation_config(model)
        config.validate()

    assert not caught
    assert config.do_sample is False
    assert config.max_new_tokens == 256
