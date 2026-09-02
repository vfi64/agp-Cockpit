from agp_cockpit.core.hermes_config import detect_model_path


def test_real_schema_prefers_model_default_over_provider_model():
    data = {
        "model": {
            "default": "qwen3.5:9b-mlx",
            "provider": "custom",
            "base_url": "http://127.0.0.1:11434/v1",
            "context_length": 65536,
        },
        "custom_providers": [
            {
                "name": "Local",
                "base_url": "http://127.0.0.1:11434/v1",
                "model": "qwen3.5:9b-mlx",
                "models_discovered": True,
            }
        ],
        "stt": {
            "local": {"model": "base"},
            "openai": {"model": "whisper-1"},
        },
    }

    path, model = detect_model_path(
        data,
        known_models=("qwen3.5:9b-mlx",),
    )

    assert path == ("model", "default")
    assert model == "qwen3.5:9b-mlx"


def test_provider_model_does_not_create_ambiguity():
    data = {
        "model": {"default": "qwen-a"},
        "custom_providers": [
            {"model": "qwen-a"},
            {"model": "qwen-b"},
        ],
    }

    path, model = detect_model_path(
        data,
        known_models=("qwen-a", "qwen-b"),
    )

    assert path == ("model", "default")
    assert model == "qwen-a"


def test_conflicting_primary_canonical_fields_fail_closed():
    data = {
        "model": {
            "default": "qwen-a",
            "name": "qwen-b",
        }
    }

    try:
        detect_model_path(
            data,
            known_models=("qwen-a", "qwen-b"),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("conflicting primary fields must fail closed")
