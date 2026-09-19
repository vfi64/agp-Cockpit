from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass


@dataclass(frozen=True)
class ClipboardResult:
    characters: int


def copy_text(root: tk.Misc, text: str) -> ClipboardResult:
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update_idletasks()
    return ClipboardResult(characters=len(text))
