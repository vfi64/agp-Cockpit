from __future__ import annotations
import subprocess

def run_osascript(script: str):
    return subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )

def open_chatgpt_in_chrome():
    return subprocess.run(
        ["/usr/bin/open", "-a", "Google Chrome", "https://chatgpt.com/"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
