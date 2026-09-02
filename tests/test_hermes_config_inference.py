from agp_cockpit.core.hermes_config import detect_model_path


def test_unique_known_local_model_can_be_inferred():
    data = {
        "defaults": {
            "model_name": "qwen3.5:9b-mlx",
            "temperature": 0.2,
        }
    }

    path, model = detect_model_path(
        data,
        known_models=("qwen3.5:9b-mlx",),
    )

    assert path == ("defaults", "model_name")
    assert model == "qwen3.5:9b-mlx"


def test_ambiguous_known_models_fail_closed():
    data = {
        "primary_model": "qwen-a",
        "fallback_model": "qwen-b",
    }

    try:
        detect_model_path(
            data,
            known_models=("qwen-a", "qwen-b"),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("ambiguous inference should fail closed")
