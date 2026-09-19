from __future__ import annotations

import subprocess


def run_osascript(script: str):
    return subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        text=True, capture_output=True, check=False,
    )

def open_chatgpt_in_chrome():
    return subprocess.run(
        ["/usr/bin/open", "-a", "Google Chrome", "https://chatgpt.com/"],
        text=True, capture_output=True, check=False,
    )
