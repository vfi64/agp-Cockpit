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


def application_support_root() -> Path:
    return settings_path().parent

def bridge_runtime_root() -> Path:
    return application_support_root() / "bridge"
