from __future__ import annotations

import argparse
import importlib.util
import plistlib
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def verify_bundle(app_path: Path) -> dict[str, object]:
    info = app_path / "Contents" / "Info.plist"
    executable = app_path / "Contents" / "MacOS" / "AGP Cockpit"
    resources = app_path / "Contents" / "Resources"
    if not info.is_file():
        raise RuntimeError(f"missing Info.plist: {info}")
    if not executable.is_file():
        raise RuntimeError(f"missing app executable: {executable}")
    data = plistlib.loads(info.read_bytes())
    if data.get("CFBundleIdentifier") != "de.vfi64.agp-cockpit":
        raise RuntimeError("unexpected bundle identifier")
    return {
        "app": str(app_path),
        "bundle_identifier": data.get("CFBundleIdentifier"),
        "executable": str(executable),
        "resources": str(resources),
    }


def build(output_dir: Path) -> Path:
    if sys.platform != "darwin":
        raise RuntimeError("macOS app packaging must run on macOS")
    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError(
            "PyInstaller is not installed. Install the project's packaging extra "
            "with: python -m pip install -e '.[packaging]'"
        )
    root = project_root()
    dist = output_dir.resolve()
    work = root / ".local" / "agp-cockpit" / "pyinstaller-work"
    spec = root / "packaging" / "macos" / "agp_cockpit.spec"
    dist.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--distpath", str(dist), "--workpath", str(work), str(spec),
        ],
        cwd=root,
        check=True,
    )
    app_path = dist / "AGP Cockpit.app"
    verify_bundle(app_path)
    return app_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the standalone AGP Cockpit macOS .app bundle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root() / ".local" / "agp-cockpit" / "dist",
    )
    parser.add_argument("--verify", type=Path, default=None)
    args = parser.parse_args()
    if args.verify is not None:
        print(verify_bundle(args.verify))
        return 0
    app = build(args.output_dir)
    print(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
