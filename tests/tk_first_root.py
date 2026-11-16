"""AGP_TK_FIRST_ROOT_IDLE_V1: consume Tk's one-time `showRootWindow` idle task on a throwaway root.

Tk 9 on macOS (macosx/tkMacOSXInit.c, TkpInit) schedules `showRootWindow` as an idle task for the first
root window of a process, once. The idle queue belongs to the thread, so the next `update()` or
`update_idletasks()` of any interpreter runs it. A first root destroyed before an idle pass leaves the task
pointing at a freed NSWindow, and the next idle pass aborts in `Tk_MacOSXGetTkWindow` (SIGTRAP, with
`update_idletasks()` SIGSEGV; crash reports of 2026-11-15, orders 2311 and 2313). Freeing the first Python
Tk object does not prevent this on the Mac (order 2313); an idle pass of the first root does. Running the
task on a root of our own, at once, takes it out of the queue for good; on other platforms this is a
harmless create-and-destroy.
"""
from __future__ import annotations


def consume_first_root_idle() -> bool:
    """True when a throwaway root ran its idle tasks and was destroyed on this thread."""
    try:
        import tkinter
    except ImportError:
        return False
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        return False
    try:
        root.withdraw()
        root.update_idletasks()   # runs the pending showRootWindow while its window still exists
    finally:
        root.destroy()
    del root
    import gc
    gc.collect()   # free the throwaway root here, on the main thread
    return True
