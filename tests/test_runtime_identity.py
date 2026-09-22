from __future__ import annotations

import json
import time


def test_runtime_identity_rejects_missing_or_mismatched_handshake(tmp_path, monkeypatch):
    from agp_cockpit.adapters import macos_extension
    from agp_cockpit.core.runtime_identity import runtime_identity_status

    repository = tmp_path / "repo"
    extension = repository / "chrome_extension"
    extension.mkdir(parents=True)
    (repository / "Download").mkdir()
    (repository / "Download" / "run_next.py").write_text("# runner\n", encoding="utf-8")
    (extension / "manifest.json").write_text(
        json.dumps({"version": "0.3.2"}),
        encoding="utf-8",
    )
    (extension / "background.js").write_text("// test\n", encoding="utf-8")
    (extension / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "build-a";\n', encoding="utf-8"
    )
    support = tmp_path / "support"
    monkeypatch.setattr(macos_extension, "settings_path", lambda: support / "settings.json")
    staged = macos_extension.stage_extension(repository)
    runtime = tmp_path / "runtime"
    runtime.mkdir()

    missing = runtime_identity_status(repository, runtime)
    assert missing["ready"] is False
    assert missing["reasons"] == ["fresh-extension-handshake-missing"]

    (runtime / "extension.json").write_text(
        json.dumps(
            {
                "version": "0.3.2",
                "build_id": "old-build",
                "page_url": "https://chatgpt.com/c/test",
                "timestamp_unix": time.time(),
            }
        ),
        encoding="utf-8",
    )
    mismatch = runtime_identity_status(repository, runtime)
    assert mismatch["ready"] is False
    assert "handshake-build-id-mismatch" in mismatch["reasons"]

    (runtime / "extension.json").unlink()
    marker_path = staged / ".agp-stage.json"
    marker_path.unlink()
    both_missing = runtime_identity_status(repository, runtime)
    assert both_missing["ready"] is False
    assert both_missing["reasons"] == [
        "staged-extension-identity-missing",
        "fresh-extension-handshake-missing",
    ]

    (runtime / "extension.json").write_text(
        json.dumps(
            {
                "version": "0.3.2",
                "build_id": "build-a",
                "page_url": "https://chatgpt.com/c/test",
                "timestamp_unix": time.time(),
            }
        ),
        encoding="utf-8",
    )
    macos_extension.stage_extension(repository)

    (runtime / "extension.json").write_text(
        json.dumps(
            {
                "version": "0.3.2",
                "build_id": "build-a",
                "page_url": "https://chatgpt.com/c/test",
                "timestamp_unix": time.time(),
            }
        ),
        encoding="utf-8",
    )
    ready = runtime_identity_status(repository, runtime)
    assert ready["ready"] is True
    assert ready["staged_extension"] == str(staged)


def test_runtime_identity_rejects_stale_handshake(tmp_path, monkeypatch):
    from agp_cockpit.adapters import macos_extension
    from agp_cockpit.core.runtime_identity import runtime_identity_status

    repository = tmp_path / "repo"
    extension = repository / "chrome_extension"
    extension.mkdir(parents=True)
    (repository / "Download").mkdir()
    (repository / "Download" / "run_next.py").write_text("# runner\n", encoding="utf-8")
    (extension / "manifest.json").write_text(json.dumps({"version": "0.3.2"}), encoding="utf-8")
    (extension / "background.js").write_text("// test\n", encoding="utf-8")
    (extension / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "build-a";\n', encoding="utf-8"
    )
    support = tmp_path / "support"
    monkeypatch.setattr(macos_extension, "settings_path", lambda: support / "settings.json")
    macos_extension.stage_extension(repository)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "extension.json").write_text(json.dumps({
        "version": "0.3.2",
        "build_id": "build-a",
        "page_url": "https://chatgpt.com/c/test",
        "timestamp_unix": time.time() - 301,
    }), encoding="utf-8")

    status = runtime_identity_status(repository, runtime, max_handshake_age_seconds=300)
    assert status["reasons"] == ["handshake-stale"]


def test_runtime_identity_rejects_foreign_conversation(tmp_path, monkeypatch):
    from agp_cockpit.adapters import macos_extension
    from agp_cockpit.core.runtime_identity import runtime_identity_status

    repository = tmp_path / "repo"
    extension = repository / "chrome_extension"
    extension.mkdir(parents=True)
    (repository / "Download").mkdir()
    (repository / "Download" / "run_next.py").write_text("# runner\n", encoding="utf-8")
    (extension / "manifest.json").write_text(json.dumps({"version": "0.3.2"}), encoding="utf-8")
    (extension / "background.js").write_text("// test\n", encoding="utf-8")
    (extension / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "build-a";\n', encoding="utf-8"
    )
    support = tmp_path / "support"
    monkeypatch.setattr(macos_extension, "settings_path", lambda: support / "settings.json")
    macos_extension.stage_extension(repository)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "extension.json").write_text(json.dumps({
        "version": "0.3.2",
        "build_id": "build-a",
        "page_url": "https://chatgpt.com/c/foreign",
        "timestamp_unix": time.time(),
    }), encoding="utf-8")

    status = runtime_identity_status(
        repository,
        runtime,
        expected_conversation_url="https://chatgpt.com/c/current",
    )
    assert status["reasons"] == ["handshake-conversation-mismatch"]


def test_runtime_identity_malformed_timestamp_fails_closed_without_crashing(tmp_path, monkeypatch):
    from agp_cockpit.adapters import macos_extension
    from agp_cockpit.core.runtime_identity import runtime_identity_status

    repository = tmp_path / "repo"
    extension = repository / "chrome_extension"
    extension.mkdir(parents=True)
    (repository / "Download").mkdir()
    (repository / "Download" / "run_next.py").write_text("# runner\n", encoding="utf-8")
    (extension / "manifest.json").write_text(json.dumps({"version": "0.3.2"}), encoding="utf-8")
    (extension / "background.js").write_text("// test\n", encoding="utf-8")
    (extension / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "build-a";\n', encoding="utf-8"
    )
    support = tmp_path / "support"
    monkeypatch.setattr(macos_extension, "settings_path", lambda: support / "settings.json")
    macos_extension.stage_extension(repository)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "extension.json").write_text(json.dumps({
        "version": "0.3.2",
        "build_id": "build-a",
        "page_url": "https://chatgpt.com/c/test",
        "timestamp_unix": "not-a-number",
    }), encoding="utf-8")

    status = runtime_identity_status(repository, runtime)
    assert status["reasons"] == ["handshake-stale"]
    assert status["handshake_timestamp_unix"] == 0.0
