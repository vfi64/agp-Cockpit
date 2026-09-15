from pathlib import Path

def test_main_window_preserves_resolved_repository_context():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert "repository_root: Path | None = None" in s
    assert "self.repository_root = (repository_root or Path.cwd()).expanduser().resolve()" in s
    assert "textvariable=self.context_var" in s
    assert "repository_root=self.repository_root" in s

def test_browser_transport_preserves_repository_context():
    s=Path("src/agp_cockpit/ui/browser_transport_panel.py").read_text(encoding="utf-8")
    assert "repository_root: Path | None = None" in s
    assert "self.repository_root = (repository_root or Path.cwd()).expanduser().resolve()" in s
    assert "repository_root=self.repository_root" in s
    assert "root = Path.cwd().resolve()" not in s

def test_gui_bootstrap_propagates_resolved_root():
    a=Path("src/agp_cockpit/app.py").read_text(encoding="utf-8")
    b=Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert "def build_root(repository_root: Path | None = None):" in a
    assert "MainWindow(root, repository_root=repository_root)" in a
    assert "def run_gui_only(repository_root: Path | None = None)" in a
    assert "def run_legacy_gui(repository_root: Path | None = None)" in b
    assert "run_gui_only(repository_root)" in b
    assert "run_legacy_gui(root)" in b
