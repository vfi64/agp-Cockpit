import pytest
import yaml

from agp_cockpit.core.hermes_writer import restore_hermes_backup, update_hermes_model


def test_updates_only_detected_top_level_model(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model: qwen-old\nprovider: custom\nbase_url: http://127.0.0.1:11434/v1\n",
        encoding="utf-8",
    )
    result = update_hermes_model("qwen-new", path=path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["model"] == "qwen-new"
    assert data["provider"] == "custom"
    assert data["base_url"] == "http://127.0.0.1:11434/v1"
    assert result.old_model == "qwen-old"
    assert result.new_model == "qwen-new"
    assert result.verified is True
    assert result.backup_path.exists()


def test_updates_nested_model_name(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model:\n  name: qwen-old\n  context_length: 65536\n",
        encoding="utf-8",
    )
    update_hermes_model("qwen-new", path=path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["model"]["name"] == "qwen-new"
    assert data["model"]["context_length"] == 65536


def test_refuses_unrecognized_model_field(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("provider:\n  selected_model: qwen-old\n", encoding="utf-8")
    with pytest.raises(ValueError):
        update_hermes_model("qwen-new", path=path)


def test_refuses_conflicting_model_fields(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("model: qwen-a\nllm:\n  model: qwen-b\n", encoding="utf-8")
    with pytest.raises(ValueError):
        update_hermes_model("qwen-new", path=path)


def test_backup_can_restore_original(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("model: qwen-old\n", encoding="utf-8")
    result = update_hermes_model("qwen-new", path=path)
    restored = restore_hermes_backup(path=path, backup_path=result.backup_path)
    assert restored.model == "qwen-old"


def test_empty_model_is_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("model: qwen-old\n", encoding="utf-8")
    with pytest.raises(ValueError):
        update_hermes_model("   ", path=path)
