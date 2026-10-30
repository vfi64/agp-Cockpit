"""AGP_NO_OWNER_PATHS_V1 (owner 2026-10-29/30): the public repository names no home folder of a real
machine. Live evidence, fixtures and scripts use <owner-checkout> or a neutral /Users/owner/…; scripts
find the checkout from their own location."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_PATH = re.compile(r"/(?:Users|home)/([A-Za-z0-9._-]+)/")
NEUTRAL = {"owner", "example", "x", "runner", "user", "claude"}


def _tracked_text_files():
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    for name in listed.decode().split("\0"):
        path = ROOT / name
        if not name or not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        try:
            yield name, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def test_no_tracked_file_names_a_personal_home_folder():
    found = sorted({f"{name}: /…/{match.group(1)}/"
                    for name, text in _tracked_text_files()
                    for match in HOME_PATH.finditer(text) if match.group(1) not in NEUTRAL})
    assert not found, found
