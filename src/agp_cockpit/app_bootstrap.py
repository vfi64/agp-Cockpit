from __future__ import annotations
from agp_cockpit.adapters.macos_settings import bridge_runtime_root, bridge_token_path
from agp_cockpit.core.runtime_root_policy import require_stable_production_runtime_root

from agp_cockpit.core.browser_readiness import start_browser_readiness_watch
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import subprocess
import time
import urllib.request

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.browser_refresh import (
    request_browser_refresh,
    wait_for_refresh_handled,
)


CHATGPT_URL = "https://chatgpt.com/"


@dataclass(frozen=True)
class StartupStatus:
    chrome_installed: bool
    chrome_started_or_reused: bool
    chatgpt_requested: bool
    bridge_ready: bool
    extension_ready: bool
    message: str


def chrome_app_path() -> Path | None:
    for candidate in (
        Path("/Applications/Google Chrome.app"),
        Path.home() / "Applications/Google Chrome.app",
    ):
        if candidate.exists():
            return candidate
    return None


def chrome_running() -> bool:
    result = subprocess.run(
        ["/usr/bin/pgrep", "-x", "Google Chrome"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def request_chatgpt_tab() -> None:
    script = r"""
tell application "Google Chrome"
    if it is not running then
        open location "https://chatgpt.com/"
        activate
        return
    end if

    repeat with w in windows
        repeat with i from 1 to count of tabs of w
            set t to tab i of w
            set u to URL of t
            if u starts with "https://chatgpt.com/" then
                set active tab index of w to i
                set index of w to 1
                activate
                return
            end if
        end repeat
    end repeat

    if (count of windows) is 0 then
        make new window
    end if
    tell window 1
        make new tab with properties {URL:"https://chatgpt.com/"}
    end tell
    activate
end tell
"""
    subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def recent_extension_handshake(
    repository_root: Path,
    *,
    max_age_seconds: float = 15.0,
) -> dict | None:
    path = (
        repository_root
        / ".local"
        / "agp-cockpit"
        / "bridge"
        / "extension.json"
    )
    data = _read_json(path)
    if not data:
        return None

    timestamp = data.get("timestamp_unix")
    if not isinstance(timestamp, (int, float)):
        return None

    if time.time() - float(timestamp) > max_age_seconds:
        return None

    return data


def wait_for_extension(
    repository_root: Path,
    *,
    timeout_seconds: float = 20.0,
    poll_seconds: float = 0.5,
) -> dict | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        handshake = recent_extension_handshake(
            repository_root,
            max_age_seconds=max(
                5.0,
                timeout_seconds + 2.0,
            ),
        )
        if handshake:
            return handshake
        time.sleep(poll_seconds)
    return None


def write_startup_status(
    repository_root: Path,
    status: StartupStatus,
) -> Path:
    root = (
        repository_root
        / ".local"
        / "agp-cockpit"
        / "startup"
    )
    root.mkdir(parents=True, exist_ok=True)

    path = root / "status.json"
    path.write_text(
        json.dumps(
            asdict(status),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def show_startup_guidance(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "AGP Cockpit – Browser-Setup",
            message,
            parent=root,
        )
        root.destroy()
    except Exception:
        print(message, flush=True)


def build_extension_guidance(
    repository_root: Path,
    *,
    extension_path: Path,
    bridge_host: str,
    bridge_port: int,
) -> str:
    token_path = bridge_token_path()
    return (
        "Chrome wurde gestartet, aber die AGP Cockpit Bridge Extension "
        "hat sich nicht beim Cockpit gemeldet.\n\n"
        "Bitte prüfen:\n"
        "1. chrome://extensions öffnen.\n"
        "2. 'AGP Cockpit Bridge' muss installiert und aktiviert sein.\n"
        f"3. Falls sie fehlt: 'Entpackte Erweiterung laden' → {extension_path}\n"
        "4. Erweiterung einmal neu laden.\n"
        f"5. Base URL in den Optionen: http://{bridge_host}:{bridge_port}\n"
        f"6. Token muss dem Inhalt von {token_path} entsprechen.\n"
        "7. ChatGPT-Tab neu laden.\n\n"
        "Das Cockpit bleibt trotzdem benutzbar."
    )


def probe_existing_bridge(
    repository_root: Path,
    *,
    bridge_host: str,
    bridge_port: int,
) -> bool:
    token_path = bridge_token_path()
    try:
        token = token_path.read_text(
            encoding="utf-8"
        ).strip()
        req = urllib.request.Request(
            f"http://{bridge_host}:{bridge_port}/v1/status",
            headers={"X-AGP-Token": token},
        )
        with urllib.request.urlopen(
            req,
            timeout=2,
        ) as response:
            return response.status == 200
    except Exception:
        return False


def run_legacy_gui(repository_root: Path | None = None) -> None:
    from agp_cockpit.app import run_gui_only

    run_gui_only(repository_root)


# AGP_DETERMINISTIC_STARTUP_WAKE_063V
def reload_exactly_one_chatgpt_tab() -> tuple[bool, str]:
    """Reload exactly one existing ChatGPT tab; fail closed on ambiguity."""
    script = r"""
tell application "Google Chrome"
    if not running then return "CHROME_NOT_RUNNING"

    set foundCount to 0
    set targetWindow to 0
    set targetTab to 0
    set targetURL to ""

    repeat with wi from 1 to count of windows
        set w to window wi
        repeat with ti from 1 to count of tabs of w
            set t to tab ti of w
            set u to URL of t
            if u starts with "https://chatgpt.com/" then
                set foundCount to foundCount + 1
                set targetWindow to wi
                set targetTab to ti
                set targetURL to u
            end if
        end repeat
    end repeat

    if foundCount is 0 then return "NO_CHATGPT_TAB"
    if foundCount is greater than 1 then return "MULTIPLE_CHATGPT_TABS:" & foundCount

    set active tab index of window targetWindow to targetTab
    set index of window targetWindow to 1
    activate
    reload tab targetTab of window targetWindow
    return "RELOADED:" & targetURL
end tell
"""
    proc = subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        text=True,
        capture_output=True,
        timeout=10,
    )
    result = proc.stdout.strip()
    if proc.returncode == 0 and result.startswith("RELOADED:"):
        return True, result
    if proc.stderr.strip():
        return False, f"{result} {proc.stderr.strip()}".strip()
    return False, result or f"osascript rc={proc.returncode}"


def run(
    repository_root: Path | None = None,
    *,
    bridge_host: str = "127.0.0.1",
    bridge_port: int = 8765,
) -> int:
    root = (
        repository_root
        or Path.cwd()
    ).expanduser().resolve()

    if chrome_app_path() is None:
        status = StartupStatus(
            chrome_installed=False,
            chrome_started_or_reused=False,
            chatgpt_requested=False,
            bridge_ready=False,
            extension_ready=False,
            message=(
                "Google Chrome wurde nicht gefunden.\n\n"
                "Bitte Chrome installieren und danach AGP Cockpit erneut starten."
            ),
        )
        write_startup_status(root, status)
        show_startup_guidance(status.message)
        run_legacy_gui(root)
        return 0

    from agp_cockpit.adapters.macos_extension import (
        ExtensionStagingError,
        stage_extension,
    )

    try:
        extension_path = stage_extension(root)
    except ExtensionStagingError as exc:
        extension_path = root / "chrome_extension"
        extension_staging_note = f" Extension staging failed: {exc}"
    else:
        extension_staging_note = ""

    runtime: BridgeRuntimeServer | None = None
    owns_runtime = False

    try:
        runtime = BridgeRuntimeServer(
            root,
            host=bridge_host,
            port=bridge_port,
            runtime_root=require_stable_production_runtime_root(bridge_runtime_root()),
        )
        runtime.start()
        owns_runtime = True
        bridge_ready = True
    except OSError as exc:
        bridge_ready = probe_existing_bridge(
            root,
            bridge_host=bridge_host,
            bridge_port=bridge_port,
        )
        if not bridge_ready:
            status = StartupStatus(
                chrome_installed=True,
                chrome_started_or_reused=chrome_running(),
                chatgpt_requested=False,
                bridge_ready=False,
                extension_ready=False,
                message=(
                    f"Port {bridge_port} auf {bridge_host} ist belegt, "
                    "aber keine kompatible AGP Cockpit Bridge antwortet.\n\n"
                    f"Technischer Hinweis: {exc}"
                ),
            )
            write_startup_status(root, status)
            show_startup_guidance(status.message)
            run_legacy_gui(root)
            return 0

    # AGP_INITIAL_HANDSHAKE_ASYNC_063R2
    # Initial extension silence is a CONNECTING condition, not an immediate
    # setup error. Manifest-V3 wake-up can be delayed substantially.
    request_chatgpt_tab()

    # AGP_DETERMINISTIC_STARTUP_WAKE_063V
    handshake = wait_for_extension(
        root,
        timeout_seconds=5.0,
        poll_seconds=0.25,
    )
    extension_ready = handshake is not None

    if not extension_ready:
        wake_ok, wake_note = reload_exactly_one_chatgpt_tab()
        if wake_ok:
            handshake = wait_for_extension(
                root,
                timeout_seconds=12.0,
                poll_seconds=0.25,
            )
            extension_ready = handshake is not None
        else:
            handshake = None


    # AGP_SKIP_REDUNDANT_POST_HANDSHAKE_REFRESH_063V_R3

    # AGP_POST_WAKE_READINESS_RECOMPUTE_063V_R4
    deterministic_browser_ready = extension_ready
    browser_connecting = not extension_ready

    # AGP_STARTUP_CONTROLFLOW_FIX_063V_R5
    if deterministic_browser_ready:
        message = (
            "AGP Cockpit bereit: Bridge, Chrome, ChatGPT "
            "und Browser-Erweiterung sind verbunden."
        )
    else:
        message = (
            "AGP Cockpit startet: Bridge und Chrome sind bereit; "
            "Browser-Erweiterung wird noch verbunden (CONNECTING)."
        )

    status = StartupStatus(
        chrome_installed=True,
        chrome_started_or_reused=True,
        chatgpt_requested=True,
        bridge_ready=bridge_ready,
        extension_ready=extension_ready,
        message=message,
    )
    write_startup_status(root, status)

    def _browser_readiness_worker() -> None:
        first = wait_for_extension(
            root,
            timeout_seconds=180.0,
            poll_seconds=0.5,
        )
        if first is None:
            failed = StartupStatus(
                chrome_installed=True,
                chrome_started_or_reused=True,
                chatgpt_requested=True,
                bridge_ready=bridge_ready,
                extension_ready=False,
                message=build_extension_guidance(
                    root,
                    extension_path=extension_path,
                    bridge_host=bridge_host,
                    bridge_port=bridge_port,
                ) + extension_staging_note,
            )
            write_startup_status(root, failed)
            return

        refresh_request = request_browser_refresh(
            root,
            reason="cockpit-startup",
        )

        connecting = StartupStatus(
            chrome_installed=True,
            chrome_started_or_reused=True,
            chatgpt_requested=True,
            bridge_ready=bridge_ready,
            extension_ready=False,
            message=(
                "AGP Cockpit Browser-Verbindung wird aktualisiert "
                "(CONNECTING)."
            ),
        )
        write_startup_status(root, connecting)

        handled = wait_for_refresh_handled(
            root,
            refresh_request.generation,
            timeout_seconds=180.0,
        )
        if not handled:
            delayed = StartupStatus(
                chrome_installed=True,
                chrome_started_or_reused=True,
                chatgpt_requested=True,
                bridge_ready=bridge_ready,
                extension_ready=False,
                message=(
                    "Browser-Erweiterung ist erreichbar, aber der angeforderte "
                    "Refresh wurde noch nicht bestätigt (CONNECTING)."
                ),
            )
            write_startup_status(root, delayed)
            return

        fresh = wait_for_extension(
            root,
            timeout_seconds=30.0,
            poll_seconds=0.5,
        )
        if fresh is None:
            delayed = StartupStatus(
                chrome_installed=True,
                chrome_started_or_reused=True,
                chatgpt_requested=True,
                bridge_ready=bridge_ready,
                extension_ready=False,
                message=(
                    "Refresh bestätigt; warte auf frischen ChatGPT-Handshake "
                    "(CONNECTING)."
                ),
            )
            write_startup_status(root, delayed)
            return

        ready = StartupStatus(
            chrome_installed=True,
            chrome_started_or_reused=True,
            chatgpt_requested=True,
            bridge_ready=bridge_ready,
            extension_ready=True,
            message=(
                "AGP Cockpit bereit: Bridge, Chrome, ChatGPT "
                "und Browser-Erweiterung sind verbunden."
            ),
        )
        path = write_startup_status(root, ready)
        try:
            import json as _json
            data = _json.loads(path.read_text(encoding="utf-8"))
            data["browser_state"] = "CONNECTED"
            path.write_text(
                _json.dumps(data, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass

    import threading as _threading
    if browser_connecting:
        _threading.Thread(
            target=_browser_readiness_worker,
            name="agp-browser-readiness",
            daemon=True,
        ).start()

    try:
        run_legacy_gui(root)
    finally:
        if owns_runtime and runtime is not None:
            runtime.stop()

    return 0
