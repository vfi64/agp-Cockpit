from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk


@dataclass(frozen=True)
class ClipboardResult:
    characters: int


def copy_text(root: tk.Misc, text: str) -> ClipboardResult:
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update_idletasks()
    return ClipboardResult(characters=len(text))
