import warnings
from types import SimpleNamespace

from transformers import GenerationConfig

from src import inference
from src.inference import deterministic_generation_config
from src.train.train_qlora import make_formatting_func


class FakeTokenizer:
    def apply_chat_template(self, messages, tokenize=False):
        return "|".join(f"{m['role']}:{m['content']}" for m in messages)


def test_formatting_func_handles_trl_batches():
    conversation = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"},
                    {"role": "assistant", "content": "[]"}]
    format_batch = make_formatting_func(FakeTokenizer())
    assert format_batch({"messages": [conversation, conversation]}) == ["system:s|user:u|assistant:[]"] * 2
    assert format_batch({"messages": conversation}) == ["system:s|user:u|assistant:[]"]


def test_detect_mode_without_gpu_uses_cpu(monkeypatch):
    import pytest
    from src.train import train_qlora

    monkeypatch.setattr(train_qlora.torch.cuda, "is_available", lambda: False)
    assert train_qlora.detect_mode("auto") == "cpu"
    assert train_qlora.detect_mode("cpu") == "cpu"
    with pytest.raises(SystemExit):
        train_qlora.detect_mode("qlora")


def test_detect_mode_with_gpu(monkeypatch):
    from src.train import train_qlora

    monkeypatch.setattr(train_qlora.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(train_qlora.importlib.util, "find_spec", lambda name: object())
    assert train_qlora.detect_mode("auto") == "qlora"
    monkeypatch.setattr(train_qlora.importlib.util, "find_spec", lambda name: None)
    assert train_qlora.detect_mode("auto") == "gpu"


def test_http_backend_returns_raw_text(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"output": "```json\n[]\n```"}

    monkeypatch.setenv("BACKEND", "http")
    monkeypatch.setenv("INFERENCE_URL", "http://localhost:9/extract")
    monkeypatch.setattr(inference.requests, "post", lambda *args, **kwargs: Response())
    assert inference.generate_raw("texto") == "```json\n[]\n```"
    assert inference.extract("texto") == []


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
    assert config.max_new_tokens == 1024


def test_generation_limit_fits_longest_expected_answer():
    import json
    from pathlib import Path

    from transformers import AutoTokenizer

    from src.inference import deterministic_generation_config

    try:
        tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", local_files_only=True)
    except OSError:
        import pytest
        pytest.skip("tokenizador do Qwen não está no cache local")
    limit = deterministic_generation_config(SimpleNamespace(generation_config=GenerationConfig())).max_new_tokens
    root = Path(__file__).resolve().parents[1]
    longest = max(
        len(tokenizer(json.loads(line)["messages"][2]["content"])["input_ids"])
        for split in ("train", "val", "test")
        for line in (root / "data" / "processed" / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    assert longest < limit
