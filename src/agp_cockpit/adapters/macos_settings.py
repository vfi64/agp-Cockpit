from __future__ import annotations

from pathlib import Path


def settings_path() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "AGP Cockpit"
        / "settings.json"
    )
