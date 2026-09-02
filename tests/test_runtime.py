import pytest
from agp_cockpit.core.runtime import find_executable, process_name_present, probe_tcp_port

def test_missing_executable_is_not_installed(monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    result = find_executable("__definitely_missing_agp_cockpit_binary__")
    assert result.path is None
    assert result.installed is False

def test_extra_candidate_can_resolve_executable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)
    candidate = tmp_path / "tool"
    candidate.write_text("#!/bin/sh\n", encoding="utf-8")
    candidate.chmod(0o755)
    result = find_executable("tool", extra_candidates=(candidate,))
    assert result.path == candidate.resolve()
    assert result.installed is True

def test_process_name_present_is_case_insensitive() -> None:
    lines = ("100 /opt/homebrew/bin/ollama serve", "200 /bin/zsh")
    assert process_name_present("OLLAMA", process_lines=lines)
    assert not process_name_present("hermes", process_lines=lines)

def test_invalid_port_is_rejected() -> None:
    with pytest.raises(ValueError):
        probe_tcp_port("127.0.0.1", 0)
