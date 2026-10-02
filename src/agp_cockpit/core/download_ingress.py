from __future__ import annotations

import re
from pathlib import Path

from agp_cockpit.core.terminal_reply import is_terminal_filename, parse_terminal_reply

MAX_DOWNLOAD_BYTES = 2_000_000


def _allowed_download_roots(repository_root: Path) -> tuple[Path, ...]:
    roots = [repository_root.expanduser().resolve() / "Download"]
    home_downloads = Path.home() / "Downloads"
    if home_downloads.exists():
        roots.append(home_downloads.resolve())
    return tuple(roots)


def _matches_download_name(actual: str, expected: str) -> bool:
    """Accept the exact name or a browser duplicate suffix: ``x (1).py`` / ``x(2).py``."""
    if actual == expected:
        return True
    pattern = re.escape(Path(expected).stem) + r" ?\(\d+\)" + re.escape(Path(expected).suffix)
    return re.fullmatch(pattern, actual) is not None


def read_downloaded_command(
    download_path: str | Path,
    expected_filename: str,
    repository_root: Path,
    allow_remote_effects: bool = False,
) -> tuple[str, str, str]:
    """Read one browser download without granting arbitrary file access."""
    del allow_remote_effects  # decided by /v1/file-loop/command
    expected = str(expected_filename).strip()
    terminal = is_terminal_filename(expected)
    if (
        not expected
        or not (terminal or expected.lower().endswith(".py"))
        or Path(expected).name != expected
    ):
        raise ValueError("exactly one safe .py or <step>_agp_terminal.json filename required")

    path = Path(download_path).expanduser().resolve()
    if not _matches_download_name(path.name, expected):
        raise ValueError("download filename does not match expected command file")
    if not any(path.parent == root for root in _allowed_download_roots(repository_root)):
        raise ValueError("download path is outside the allowed download directories")
    if not path.is_file():
        raise ValueError("downloaded command file is not readable")
    if path.stat().st_size < 1 or path.stat().st_size > MAX_DOWNLOAD_BYTES:
        raise ValueError("downloaded command file size outside bounded range")
    content = path.read_text(encoding="utf-8")
    if terminal:
        parse_terminal_reply(expected, content)
        return expected, content, "application/json"
    # AGP_INGRESS_SAFETY_ONLY_V1 (live 2026-10-02, step 1568): fetching checks
    # only name, location, size and UTF-8. Every semantic check, syntax
    # included, belongs to /v1/file-loop/command, which answers a violation
    # with a bounded correction instead of a hard stop
    # (AGP_CORRECTABLE_REJECTION_V1); here a "missing --self-test" stopped the
    # mission of a fresh chat.
    return expected, content, "text/x-python"
