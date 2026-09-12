from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from agp_cockpit.ui.mission_operator_window import (
    MissionOperatorWindow,
)


class BrowserTransportPanel(ttk.LabelFrame):
    """
    Existing browser transport panel with a direct Mission Operator entry point.

    The browser transport implementation remains in the Chrome extension /
    localhost bridge. This panel gives the local Cockpit a visible path to
    the same persistent mission state.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        get_result_text,
        set_work_order_text,
        repository_root: Path | None = None,
    ) -> None:
        super().__init__(
            master,
            text="Browser-Transport",
            padding=8,
        )
        self.get_result_text = get_result_text
        self.set_work_order_text = set_work_order_text
        self.repository_root = (repository_root or Path.cwd()).expanduser().resolve()

        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text=(
                "ChatGPT ↔ Chrome Bridge ↔ AGP Cockpit"
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        buttons = ttk.Frame(self)
        buttons.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        self.mission_operator_button = ttk.Button(
            buttons,
            text="Mission Operator öffnen",
            command=self.open_operator,
            takefocus=True,
        )
        self.mission_operator_button.pack(side="left")

        ttk.Label(
            self,
            text=(
                "Mission-State, DRY_RUN/LIVE und SINGLE_STEP/FULL_AUTO "
                "werden persistent unter .local geführt."
            ),
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(6, 0),
        )

    def open_operator(self) -> None:
        MissionOperatorWindow(
            self.winfo_toplevel(),
            repository_root=self.repository_root,
        )
