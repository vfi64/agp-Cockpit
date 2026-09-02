from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

from agp_cockpit.core.clipboard import copy_text
from agp_cockpit.core.terminal_policy import ExecutionPolicy
from agp_cockpit.core.work_order import parse_work_order_json
from agp_cockpit.core.work_order_runner import (
    execute_work_order,
    preview_work_order,
)


class WorkOrderPanel(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        repository_root: Path,
    ) -> None:
        super().__init__(master, padding=8)
        self.repository_root = repository_root.resolve()
        self.kit_binary = self.repository_root / '.venv/bin/agentic-kit'
        self.policy = ExecutionPolicy(
            repository_root=self.repository_root,
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)

        ttk.Label(
            self,
            text=(
                "Strukturierter JSON-Auftrag: erst prüfen, dann ausdrücklich ausführen."
            ),
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.input_text = tk.Text(
            self,
            height=7,
            wrap="none",
        )
        self.input_text.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        buttons = ttk.Frame(self)
        buttons.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(6, 6),
        )

        ttk.Button(
            buttons,
            text="Beispiel",
            command=self.insert_example,
        ).grid(row=0, column=0, padx=(0, 6))

        ttk.Button(
            buttons,
            text="Prüfen",
            command=self.preview,
        ).grid(row=0, column=1, padx=(0, 6))

        self.execute_button = ttk.Button(
            buttons,
            text="Ausführen",
            command=self.execute,
            state="disabled",
        )
        self.execute_button.grid(row=0, column=2, padx=(0, 6))

        self.copy_button = ttk.Button(
            buttons,
            text="Ergebnis kopieren",
            command=self.copy_result,
            state="disabled",
        )
        self.copy_button.grid(row=0, column=3)

        ttk.Label(
            self,
            text="Vorschau / Ergebnis",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=(0, 4),
        )

        self.output_text = tk.Text(
            self,
            height=10,
            wrap="word",
            state="disabled",
        )
        self.output_text.grid(
            row=4,
            column=0,
            sticky="nsew",
        )

        self._approved_input: str | None = None

    def _set_output(self, text: str) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.configure(state="disabled")

    def insert_example(self) -> None:
        payload = {
            "label": "AGP Cockpit Testauftrag",
            "cwd": str(self.repository_root),
            "argv": [
                "/usr/bin/printf",
                "Hallo vom AGP Cockpit\n",
            ],
            "timeout_seconds": 10,
        }
        self.input_text.delete("1.0", "end")
        self.input_text.insert(
            "1.0",
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
        )
        self.execute_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self._approved_input = None

    def _parse_current(self):
        raw = self.input_text.get("1.0", "end").strip()
        if not raw:
            raise ValueError("Kein Auftrag eingegeben")
        return raw, parse_work_order_json(raw)

    def preview(self) -> None:
        try:
            raw, order = self._parse_current()
            preview = preview_work_order(
                order,
                policy=self.policy,
                kit_binary=self.kit_binary,
            )
        except Exception as exc:
            self.execute_button.configure(state="disabled")
            self.copy_button.configure(state="disabled")
            self._approved_input = None
            self._set_output(f"BLOCKED: {exc}")
            return

        self._approved_input = raw
        self.execute_button.configure(state="normal")
        self.copy_button.configure(state="disabled")
        self._set_output(
            "GEPRÜFTE VORSCHAU\n\n"
            + preview.preview_text
            + "\n\nNoch wurde nichts ausgeführt."
        )

    def execute(self) -> None:
        try:
            raw, order = self._parse_current()
        except Exception as exc:
            self.execute_button.configure(state="disabled")
            self.copy_button.configure(state="disabled")
            self._approved_input = None
            self._set_output(f"BLOCKED: {exc}")
            return

        if self._approved_input != raw:
            self.execute_button.configure(state="disabled")
            self.copy_button.configure(state="disabled")
            self._approved_input = None
            self._set_output(
                "BLOCKED: Auftrag wurde seit der Vorschau verändert. "
                "Bitte erneut prüfen."
            )
            return

        if not messagebox.askyesno(
            "Lokalen Auftrag ausführen",
            "Der geprüfte Auftrag wird jetzt lokal ausgeführt.\n\nFortfahren?",
            parent=self.winfo_toplevel(),
        ):
            return

        self.execute_button.configure(state="disabled")

        try:
            run = execute_work_order(
                order,
                policy=self.policy,
                kit_binary=self.kit_binary,
            )
        except Exception as exc:
            self.copy_button.configure(state="disabled")
            self._set_output(f"FAIL: {exc}")
            return

        self._set_output(run.result_block)
        self.copy_button.configure(state="normal")

    def copy_result(self) -> None:
        text = self.get_result_for_copy()
        if not text:
            return
        result = copy_text(
            self.winfo_toplevel(),
            text,
        )
        messagebox.showinfo(
            "Ergebnis kopiert",
            f"{result.characters} Zeichen wurden in die Zwischenablage kopiert.",
            parent=self.winfo_toplevel(),
        )

    def set_work_order_text(self, text: str) -> None:
        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", text)
        self.execute_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self._approved_input = None
        self._set_output(
            "Auftrag übernommen. Bitte zuerst prüfen."
        )

    def get_result_for_copy(self) -> str:
        return self.output_text.get("1.0", "end").rstrip()
