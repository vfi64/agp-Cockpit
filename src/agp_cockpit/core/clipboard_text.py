from __future__ import annotations

import subprocess


def read_macos_clipboard() -> str:
    completed = subprocess.run(
        ["/usr/bin/pbpaste"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "Zwischenablage konnte nicht gelesen werden"
        )
    return completed.stdout


def write_macos_clipboard(text: str) -> None:
    completed = subprocess.run(
        ["/usr/bin/pbcopy"],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "Zwischenablage konnte nicht geschrieben werden"
        )
