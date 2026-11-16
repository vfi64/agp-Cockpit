"""AGP_TK_FIRST_ROOT_IDLE_V1 probe (run as a process; pytest does not collect this file).

Modes:
  stale      the first root is destroyed before an idle pass, then a second root runs update(): on macOS
             Tk 9 the pending showRootWindow touches the freed window (SIGTRAP)
  prewarmed  consume_first_root_idle() first (as tests/conftest.py does), then the stale sequence
Prints „survived“ and exits 0 when the process lives through the second root's update().

Usage: python tests/tk_first_root_probe.py stale|prewarmed
"""
from __future__ import annotations

import sys

from tk_first_root import consume_first_root_idle


def main(mode: str) -> int:
    import tkinter as tk

    if mode not in ("stale", "prewarmed"):
        print(f"unknown mode {mode}", file=sys.stderr)
        return 2
    if mode == "prewarmed" and not consume_first_root_idle():
        print("no Tk root possible", file=sys.stderr)
        return 3
    first = tk.Tk()
    first.attributes("-alpha", 0.0)   # hidden as tests/conftest.py hides test windows
    first.destroy()              # no idle pass: the first root's showRootWindow is still pending
    second = tk.Tk()
    second.withdraw()
    second.update()              # runs the thread's idle queue
    second.destroy()
    print("survived", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
