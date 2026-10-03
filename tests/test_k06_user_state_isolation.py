from pathlib import Path

from agp_cockpit.adapters.macos_context import persist_repository_root
from agp_cockpit.adapters.macos_settings import settings_path
from agp_cockpit.settings import AppSettings


def _valid_repo(path: Path) -> Path:
    path.mkdir()
    (path / "chrome_extension").mkdir()
    (path / ".agentic").mkdir()
    (path / ".git").mkdir()
    return path


def test_settings_path_is_inside_test_home():
    path = settings_path()
    assert path.is_relative_to(Path.home())
    assert str(path).endswith("Library/Application Support/AGP Cockpit/settings.json")


def test_repository_persistence_cannot_escape_test_home(tmp_path):
    repo = _valid_repo(tmp_path / "repo")
    updated = persist_repository_root(AppSettings(), repo)
    path = settings_path()
    assert path.exists()
    assert path.is_relative_to(Path.home())
    assert updated.repository_root == str(repo.resolve())
    assert "pytest-" in str(Path.home()) or "/private/var/" in str(Path.home())
