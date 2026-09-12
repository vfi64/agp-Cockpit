from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agp_cockpit.adapters.macos_settings import settings_path
from agp_cockpit.settings import AppSettings, save_settings


def looks_like_repository_context(path: Path) -> bool:
    root = path.expanduser().resolve()
    return root.is_dir() and (root / "chrome_extension").is_dir() and (root / ".agentic").is_dir()



def resolve_repository_root(
    *,
    explicit_root: Path | None,
    settings: AppSettings,
    cwd: Path,
    chooser=None,
) -> tuple[Path | None, str]:
    if explicit_root is not None:
        root = explicit_root.expanduser().resolve()
        return (root, "explicit") if looks_like_repository_context(root) else (None, "invalid-explicit")

    if settings.repository_root:
        saved = Path(settings.repository_root).expanduser().resolve()
        if looks_like_repository_context(saved):
            return saved, "settings"

    cwd = cwd.expanduser().resolve()
    if looks_like_repository_context(cwd):
        return cwd, "cwd"

    if chooser is None:
        return None, "unresolved"
    selected = chooser()
    if not selected:
        return None, "cancelled"
    selected_root = Path(selected).expanduser().resolve()
    if not looks_like_repository_context(selected_root):
        return None, "invalid-selection"
    return selected_root, "chooser"


def choose_repository_root() -> str | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        selected = filedialog.askdirectory(
            title="AGP Cockpit – Repository auswählen",
            mustexist=True,
        )
    finally:
        root.destroy()
    return selected or None


def persist_repository_root(settings: AppSettings, root: Path) -> AppSettings:
    resolved = root.expanduser().resolve()
    if not looks_like_repository_context(resolved):
        raise ValueError("repository root is not a valid AGP Cockpit repository context")
    updated = replace(settings, repository_root=str(resolved))
    save_settings(settings_path(), updated)
    return updated
