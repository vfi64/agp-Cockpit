from pathlib import Path

import agp_cockpit.core.hermes_runtime as runtime


def test_configured_model_availability(monkeypatch, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("model: qwen3.5:9b-mlx\n", encoding="utf-8")

    class Executable:
        path = Path("/usr/local/bin/hermes")

    monkeypatch.setattr(
        runtime,
        "find_executable",
        lambda *a, **k: Executable(),
    )

    info = runtime.discover_hermes_runtime(
        ollama_models=("qwen3.5:9b-mlx",),
        config_path=config,
    )

    assert info.config.model == "qwen3.5:9b-mlx"
    assert info.configured_model_available is True
