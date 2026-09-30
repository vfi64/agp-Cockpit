#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

MAX_OUTPUT_BYTES = 256 * 1024


def banner(text: str) -> None:
    line = "=" * 71
    print(f"\n{line}\n=== {text} ===\n{line}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_response_artifacts(download: Path) -> set[Path]:
    return {
        path.resolve()
        for path in download.glob("*_return_bundle.json")
        if path.is_file()
    }


def run(cmd: list[str], cwd: Path) -> None:
    print("\n$ " + " ".join(str(x) for x in cmd), flush=True)
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="", flush=True)

    returncode = proc.wait()
    print(f"[rc={returncode}]", flush=True)
    if returncode != 0:
        banner("RUN_NEXT STOPPED - STAGE FAILED")
        raise SystemExit(returncode)

def select_script(download: Path, selector: str) -> Path:
    # Exact filename/path is accepted as well as a step prefix such as 080B.
    candidate = Path(selector).expanduser()
    candidates = [candidate]
    if not candidate.is_absolute():
        candidates.append(download / candidate)
    for exact in candidates:
        if exact.is_file():
            return exact.resolve()

    selectors = [selector]
    if selector.isdigit():
        selectors.append(f"{int(selector):03d}")
    selectors = list(dict.fromkeys(selectors))
    matches = sorted(
        p for prefix in selectors
        for p in download.glob(f"{prefix}_*.py")
        if p.name != Path(__file__).name
        and not p.name.endswith(".bak")
        and "~" not in p.name
    )
    if not matches:
        raise SystemExit(f"No script matching {selector}_*.py in {download}")
    if len(matches) > 1:
        names = "\n  ".join(p.name for p in matches)
        raise SystemExit(
            f"Ambiguous selector {selector!r}; matches:\n  {names}\n"
            "Use the exact filename."
        )
    return matches[0]


class TeeStream:
    def __init__(self, terminal, log, budget):
        self.terminal = terminal
        self.log = log
        self.budget = budget

    def write(self, text):
        encoded = str(text).encode("utf-8", errors="replace")
        remaining = MAX_OUTPUT_BYTES - self.budget["used"]
        if remaining > 0:
            if len(encoded) <= remaining:
                bounded = encoded
            else:
                marker = (
                    f"\n...[AGP RUN_NEXT OUTPUT TRUNCATED; "
                    f"limit_bytes={MAX_OUTPUT_BYTES}]...\n"
                ).encode()
                bounded = (encoded[:max(0, remaining - len(marker))] + marker)[:remaining]
                self.budget["truncated"] = True
            text_to_write = bounded.decode("utf-8", errors="replace")
            self.terminal.write(text_to_write)
            self.log.write(text_to_write)
            self.budget["used"] += len(bounded)
        elif not self.budget["truncated"]:
            marker = (
                f"\n...[AGP RUN_NEXT OUTPUT TRUNCATED; "
                f"limit_bytes={MAX_OUTPUT_BYTES}]...\n"
            )
            self.terminal.write(marker)
            self.log.write(marker)
            self.budget["truncated"] = True
        self.log.flush()
        return len(text)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    @property
    def encoding(self):
        return getattr(self.terminal, "encoding", "utf-8")

    def isatty(self):
        fn = getattr(self.terminal, "isatty", None)
        return bool(fn()) if fn else False


def snapshot_path(download: Path, selector: str) -> Path | None:
    """Return a non-overwriting, step-scoped copy path for the runner log."""
    match = re.match(r"^(\d+)(?:_|$)", Path(selector).name)
    if match is None:
        return None
    prefix = match.group(1)
    target = download / f"{prefix}_run_next_output.txt"
    if target.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        target = download / f"{prefix}_run_next_output_{stamp}.txt"
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely run one numbered AGP Cockpit work script."
    )
    parser.add_argument(
        "selector",
        help="Step prefix (e.g. 080B) or exact script filename/path",
    )
    args = parser.parse_args()

    download = Path(__file__).resolve().parent
    repo = download.parent
    script = select_script(download, args.selector)
    project_python = repo / ".venv" / "bin" / "python"
    child_python = str(project_python) if project_python.is_file() else sys.executable

    banner("AGP COCKPIT RUN_NEXT")
    print(f"Repository : {repo}")
    print(f"Script     : {script}")
    print(f"SHA-256    : {sha256(script)}")
    print(f"Python     : {child_python}")

    run([child_python, "-m", "py_compile", str(script)], repo)
    # SELF_TEST_SIDE_EFFECT_GUARD
    before_bundles = {p.resolve() for p in download.glob("*_return_bundle.json") if p.is_file()}
    run([child_python, str(script), "--self-test"], repo)
    after_bundles = {p.resolve() for p in download.glob("*_return_bundle.json") if p.is_file()}
    created_by_self_test = sorted(after_bundles - before_bundles)
    if created_by_self_test:
        names = "\n  ".join(str(p) for p in created_by_self_test)
        raise SystemExit(
            "Self-test produced canonical response artifact(s); "
            "real run suppressed to prevent duplicate execution:\n  " + names
        )

    banner("SELF-TEST PASSED - STARTING REAL RUN")
    before_real_run = canonical_response_artifacts(download)
    run([child_python, str(script)], repo)
    after_real_run = canonical_response_artifacts(download)
    created_by_real_run = sorted(after_real_run - before_real_run)
    if len(created_by_real_run) != 1:
        banner("RUN_NEXT STOPPED - RESULT CONTRACT FAILED")
        print(
            "The real run must create exactly one new *_return_bundle.json; "
            f"created {len(created_by_real_run)}."
        )
        raise SystemExit(2)
    try:
        import json

        result = json.loads(created_by_real_run[0].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        banner("RUN_NEXT STOPPED - RESULT CONTRACT FAILED")
        print(f"The return bundle is not valid JSON: {type(exc).__name__}: {exc}")
        raise SystemExit(2)
    if not isinstance(result, dict):
        banner("RUN_NEXT STOPPED - RESULT CONTRACT FAILED")
        print("The return bundle must contain exactly one JSON object.")
        raise SystemExit(2)

    banner("RUN_NEXT PASS")
    return 0


if __name__ == "__main__":
    download_path = Path(__file__).resolve().parent
    output_path = download_path / "__run_next_output.txt"
    snapshot = snapshot_path(download_path, sys.argv[1]) if len(sys.argv) > 1 else None
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    exit_code = 0
    try:
        with output_path.open("w", encoding="utf-8", buffering=1) as log:
            budget = {"used": 0, "truncated": False}
            sys.stdout = TeeStream(original_stdout, log, budget)
            sys.stderr = TeeStream(original_stderr, log, budget)
            try:
                exit_code = main()
            except SystemExit as exc:
                if isinstance(exc.code, int):
                    exit_code = exc.code
                else:
                    print(str(exc.code), file=sys.stderr, flush=True)
                    exit_code = 1
            finally:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                finally:
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
    finally:
        if snapshot is not None:
            shutil.copyfile(output_path, snapshot)
    raise SystemExit(exit_code)
