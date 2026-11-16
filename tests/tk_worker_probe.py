"""AGP_TK_WORKER_PLAIN_VALUES_V1 probe (run as a process; pytest does not collect this file).

A test-like sequence: a Standard-Tasks panel starts its Lage worker, the Lage takes a while (like
`git ls-remote origin` on a slow network), the test destroys its window and collects on the main
thread; afterwards another thread runs the garbage collection (in the suite: a bridge server thread or
the next panel's worker). If the worker held the panel, the old window is freed on that foreign thread
and Tcl aborts the process („Tcl_AsyncDelete: async handler deleted by the wrong thread“; SIGTRAP on
the owner's Mac). Exit 0 with „survived“ when the worker held plain values only.

Usage: PYTHONPATH=src python tests/tk_worker_probe.py <empty folder>
"""
from __future__ import annotations

import gc
import sys
import threading
import time
from pathlib import Path

DELAY = 0.6


def main(repository_root: Path) -> int:
    import tkinter as tk

    from agp_cockpit.core import chrome_automation, repo_state
    from agp_cockpit.ui import standard_tasks_panel as panel_module

    def refuse(_script):
        raise OSError("no host Chrome in the probe")

    def slow_lage(_root, **_kwargs):
        time.sleep(DELAY)
        raise RuntimeError("probe: no Lage")

    chrome_automation._run_osascript = refuse
    panel_module.bridge_status = lambda: {"mission": None}
    repo_state.lagebericht = slow_lage

    def a_test() -> None:
        root = tk.Tk()
        root.withdraw()
        panel = panel_module.StandardTasksPanel(root, repository_root=repository_root)
        panel.refresh_lage()
        root.update()
        root.destroy()
        panel = root = None
        gc.collect()   # the suite's teardown (AGP_TK_GC_ON_MAIN_THREAD_V1)

    a_test()
    time.sleep(DELAY + 0.4)   # the worker ends during the next, non-Tk test
    collector = threading.Thread(target=gc.collect, name="probe-foreign-gc")
    collector.start()
    collector.join()
    print("survived", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
