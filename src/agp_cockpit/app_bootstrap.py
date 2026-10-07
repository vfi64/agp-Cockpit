from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from agp_cockpit.adapters.macos_browser import run_chrome_automation
from agp_cockpit.adapters.macos_extension import (
    _manifest_build_id,
    _manifest_version,
    local_extension_root,
)
from agp_cockpit.adapters.macos_settings import bridge_runtime_root, bridge_token_path
from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.browser_refresh import (
    request_browser_refresh,
    wait_for_refresh_handled,
)
from agp_cockpit.core.runtime_root_policy import require_stable_production_runtime_root

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
        check=False,
    )
    return result.returncode == 0


def request_chatgpt_tab() -> tuple[bool, str]:
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
    return run_chrome_automation(script)


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _stage_marker(path: Path) -> dict:
    data = _read_json(path / ".agp-stage.json")
    return data or {}


def recent_extension_handshake(
    repository_root: Path,
    *,
    runtime_root: Path | None = None,
    max_age_seconds: float = 15.0,
) -> dict | None:
    del repository_root  # retained for the public startup helper API
    path = (runtime_root or bridge_runtime_root()).expanduser().resolve() / "extension.json"
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
    runtime_root: Path | None = None,
    timeout_seconds: float = 20.0,
    poll_seconds: float = 0.5,
) -> dict | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        handshake = recent_extension_handshake(
            repository_root,
            runtime_root=runtime_root,
            max_age_seconds=max(
                5.0,
                timeout_seconds + 2.0,
            ),
        )
        if handshake:
            return handshake
        time.sleep(poll_seconds)
    return None


def wait_for_matching_extension(
    repository_root: Path,
    extension_path: Path,
    *,
    runtime_root: Path | None = None,
    timeout_seconds: float = 30.0,
    poll_seconds: float = 0.5,
) -> dict | None:
    """Wait for a fresh handshake from the staged extension build."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        handshake = recent_extension_handshake(
            repository_root,
            runtime_root=runtime_root,
            max_age_seconds=max(5.0, timeout_seconds + 2.0),
        )
        if extension_matches_staged_build(handshake, extension_path):
            return handshake
        time.sleep(poll_seconds)
    return None


def extension_matches_staged_build(handshake: dict | None, extension_path: Path) -> bool:
    """Accept only a handshake emitted by the currently staged extension."""
    if not handshake:
        return False
    try:
        expected = _manifest_version(extension_path)
        expected_build_id = _manifest_build_id(extension_path)
    except Exception:  # noqa: BLE001 - readiness must fail closed.
        return False
    return (
        str(handshake.get("version", "")).strip() == expected
        and str(handshake.get("build_id", "")).strip() == expected_build_id
    )


def write_startup_status(
    repository_root: Path,
    status: StartupStatus,
) -> Path:
    from agp_cockpit.core.runtime_paths import runtime_dir  # AGP_RUNTIME_HOME_V1
    root = runtime_dir(repository_root, "startup")
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
    except Exception:  # noqa: BLE001 - GUI fallback must never block startup.
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
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except Exception:  # noqa: BLE001 - bridge probing is best-effort.
        return False
    # AGP_REPOSITORY_SWITCH_V1: a bridge still bound to another repository
    # (e.g. right after a switch) is not reused.
    return bridge_serves_repository(payload, repository_root)


def bridge_serves_repository(payload, repository_root: Path) -> bool:
    expected = str(Path(repository_root).expanduser().resolve())
    found = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "repository_root" and isinstance(value, str):
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return bool(found) and all(str(Path(v).expanduser().resolve()) == expected for v in found)


def run_legacy_gui(repository_root: Path | None = None, local_contract=None) -> None:
    from agp_cockpit.app import run_gui_only

    run_gui_only(repository_root, local_contract=local_contract)


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
    ok, result = run_chrome_automation(script)
    if ok and result.startswith("RELOADED:"):
        return True, result
    return False, result or "Chrome did not confirm a tab reload."


def reload_active_chatgpt_tab() -> tuple[bool, str]:
    """Reload the already selected ChatGPT tab without guessing among tabs."""
    script = r'''
tell application "Google Chrome"
    if not running then return "CHROME_NOT_RUNNING"
    if (count of windows) = 0 then return "NO_CHROME_WINDOW"
    set w to front window
    if (count of tabs of w) = 0 then return "NO_CHROME_TAB"
    set t to active tab of w
    set u to URL of t
    if u does not start with "https://chatgpt.com/" then return "ACTIVE_TAB_NOT_CHATGPT"
    reload t
    return "RELOADED:" & u
end tell
'''
    ok, result = run_chrome_automation(script)
    if ok and result.startswith("RELOADED:"):
        return True, result
    return False, result or "Chrome did not confirm the active ChatGPT tab reload."


def run(
    repository_root: Path | None = None,
    *,
    bridge_host: str = "127.0.0.1",
    bridge_port: int = 8765,
    local_contract=None,
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
        run_legacy_gui(root, local_contract=local_contract)
        return 0

    from agp_cockpit.adapters.macos_extension import (
        ExtensionStagingError,
        stage_extension,
    )

    stage_before = _stage_marker(local_extension_root())
    try:
        extension_path = stage_extension(root)
    except ExtensionStagingError as exc:
        extension_path = root / "chrome_extension"
        extension_staging_note = f" Extension staging failed: {exc}"
    else:
        extension_staging_note = ""
    stage_after = _stage_marker(extension_path)
    stage_changed = stage_before != stage_after

    runtime: BridgeRuntimeServer | None = None
    owns_runtime = False

    try:
        runtime_root = require_stable_production_runtime_root(bridge_runtime_root())
        runtime = BridgeRuntimeServer(
            root,
            host=bridge_host,
            port=bridge_port,
            runtime_root=runtime_root,
            local_task_contract=local_contract,
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
            run_legacy_gui(root, local_contract=local_contract)
            return 0

    # AGP_INITIAL_HANDSHAKE_ASYNC_063R2
    # Initial extension silence is a CONNECTING condition, not an immediate
    # setup error. Manifest-V3 wake-up can be delayed substantially.
    chatgpt_requested, browser_navigation_note = request_chatgpt_tab()

    # AGP_DETERMINISTIC_STARTUP_WAKE_063V
    handshake = None
    extension_ready = False
    if not stage_changed:
        handshake = wait_for_extension(
            root,
            runtime_root=runtime_root,
            timeout_seconds=5.0,
            poll_seconds=0.25,
        )
        extension_ready = extension_matches_staged_build(handshake, extension_path)

    if not extension_ready:
        wake_ok, wake_note = reload_exactly_one_chatgpt_tab()
        if wake_ok:
            handshake = wait_for_extension(
                root,
                runtime_root=runtime_root,
                timeout_seconds=12.0,
                poll_seconds=0.25,
            )
            extension_ready = extension_matches_staged_build(handshake, extension_path)
        else:
            handshake = None
            extension_staging_note += f" Wake-up not confirmed: {wake_note}."


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
    if not chatgpt_requested:
        message += f" Browser navigation: {browser_navigation_note}"

    status = StartupStatus(
        chrome_installed=True,
        chrome_started_or_reused=True,
        chatgpt_requested=chatgpt_requested,
        bridge_ready=bridge_ready,
        extension_ready=extension_ready,
        message=message,
    )
    write_startup_status(root, status)

    def _browser_readiness_worker() -> None:
        first = wait_for_extension(
            root,
            runtime_root=runtime_root,
            timeout_seconds=180.0,
            poll_seconds=0.5,
        )
        if first is None:
            failed = StartupStatus(
                chrome_installed=True,
                chrome_started_or_reused=True,
                chatgpt_requested=chatgpt_requested,
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

        refresh_request = None
        if not extension_matches_staged_build(first, extension_path):
            try:
                target_build = _manifest_build_id(extension_path)
            except Exception:  # noqa: BLE001 - the bridge falls back to its own build id
                target_build = ""
            refresh_request = request_browser_refresh(
                root,
                reason="staged-extension-version-mismatch",
                target_build_id=target_build,
            )
            wake_ok, wake_note = reload_active_chatgpt_tab()
            if not wake_ok:
                # AGP_EXTENSION_AUTO_REFRESH_V2: the AppleScript wake only speeds
                # things up; the extension picks the request up at its next
                # contact (live 2026-10-02: ACTIVE_TAB_NOT_CHATGPT aborted here
                # although the refresh then succeeded). Keep waiting.
                write_startup_status(root, StartupStatus(
                    chrome_installed=True,
                    chrome_started_or_reused=True,
                    chatgpt_requested=chatgpt_requested,
                    bridge_ready=bridge_ready,
                    extension_ready=False,
                    message=(
                        "Browser-Erweiterung veraltet; sie lädt sich beim nächsten Kontakt "
                        f"selbst neu (Tab-Reload nicht möglich: {wake_note})."
                    ),
                ))

            refresh_confirmed = wait_for_refresh_handled(
                root,
                refresh_request.generation,
                timeout_seconds=60.0,
            )
            if not refresh_confirmed:
                # The extension can reload successfully but report the
                # handled-generation marker after the first wait window. A
                # current matching handshake is stronger evidence than an
                # expired marker wait and must reconcile startup safely.
                refresh_confirmed = (
                    wait_for_matching_extension(
                        root,
                        extension_path,
                        runtime_root=runtime_root,
                        timeout_seconds=120.0,
                    )
                    is not None
                )
            if not refresh_confirmed:
                failed = StartupStatus(
                    chrome_installed=True,
                    chrome_started_or_reused=True,
                    chatgpt_requested=chatgpt_requested,
                    bridge_ready=bridge_ready,
                    extension_ready=False,
                    message=(
                        "Der automatische Extension-Refresh wurde nicht bestätigt; "
                        "kein Task-Start freigegeben."
                    ),
                )
                write_startup_status(root, failed)
                return

        if refresh_request is None:
            refresh_request = request_browser_refresh(
                root,
                reason="cockpit-startup",
            )

        connecting = StartupStatus(
            chrome_installed=True,
            chrome_started_or_reused=True,
            chatgpt_requested=chatgpt_requested,
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
            handled = (
                wait_for_matching_extension(
                    root,
                    extension_path,
                    runtime_root=runtime_root,
                    timeout_seconds=30.0,
                )
                is not None
            )
        if not handled:
            delayed = StartupStatus(
                chrome_installed=True,
                chrome_started_or_reused=True,
                chatgpt_requested=chatgpt_requested,
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
            runtime_root=runtime_root,
            timeout_seconds=30.0,
            poll_seconds=0.5,
        )
        if fresh is None or not extension_matches_staged_build(fresh, extension_path):
            delayed = StartupStatus(
                chrome_installed=True,
                chrome_started_or_reused=True,
                chatgpt_requested=chatgpt_requested,
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
            chatgpt_requested=chatgpt_requested,
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
        except Exception:  # noqa: BLE001 - telemetry persistence is best-effort.
            return

    import threading as _threading
    if browser_connecting:
        _threading.Thread(
            target=_browser_readiness_worker,
            name="agp-browser-readiness",
            daemon=True,
        ).start()

    try:
        run_legacy_gui(root, local_contract=local_contract)
    finally:
        if owns_runtime and runtime is not None:
            runtime.stop()

    return 0
