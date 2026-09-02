from __future__ import annotations

import argparse
from pathlib import Path
import signal
import sys
import threading

from agp_cockpit.core.bridge_runtime_server import (
    BridgeRuntimeServer,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agp_cockpit.bridge_main",
        description="Run the local AGP Cockpit bridge service.",
    )
    parser.add_argument(
        "--repository",
        default=".",
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    runtime = BridgeRuntimeServer(
        Path(args.repository),
        host=args.host,
        port=args.port,
    )
    info = runtime.start()

    print("AGP Cockpit Bridge READY", flush=True)
    print(f"HOST={info.host}", flush=True)
    print(f"PORT={info.port}", flush=True)
    print(
        "TOKEN_FILE="
        + str(
            runtime.local_root / "token.txt"
        ),
        flush=True,
    )
    print(
        "Configure the Chrome extension with this token.",
        flush=True,
    )

    stop_event = threading.Event()

    def stop_handler(signum, frame):
        stop_event.set()

    signal.signal(
        signal.SIGINT,
        stop_handler,
    )
    signal.signal(
        signal.SIGTERM,
        stop_handler,
    )

    try:
        while not stop_event.wait(0.5):
            pass
    finally:
        runtime.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
