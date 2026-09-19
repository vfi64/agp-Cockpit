from agp_cockpit.core.hermes_config import (
    detect_model_path,
    read_hermes_config,
)


def test_detect_top_level_model():
    path, value = detect_model_path({"model": "qwen3.5:9b-mlx"})
    assert path == ("model",)
    assert value == "qwen3.5:9b-mlx"

def test_detect_nested_model_name():
    path, value = detect_model_path(
        {"model": {"name": "qwen3.5:9b-mlx"}}
    )
    assert path == ("model", "name")
    assert value == "qwen3.5:9b-mlx"

def test_read_missing_config(tmp_path):
    info = read_hermes_config(tmp_path / "missing.yaml")
    assert info.exists is False
    assert info.model is None

def test_read_realistic_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model: qwen3.5:9b-mlx\n"
        "provider: custom\n"
        "base_url: http://127.0.0.1:11434/v1\n",
        encoding="utf-8",
    )
    info = read_hermes_config(path)
    assert info.exists is True
    assert info.model == "qwen3.5:9b-mlx"
    assert info.model_path == ("model",)

def test_conflicting_supported_model_fields_are_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model: qwen-a\n"
        "llm:\n"
        "  model: qwen-b\n",
        encoding="utf-8",
    )
    info = read_hermes_config(path)
    assert info.error is not None
    assert info.model is None
