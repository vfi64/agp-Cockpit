import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_OUTPUT_BYTES = 256 * 1024


def test_canonical_run_next_bounds_child_output_and_log(tmp_path: Path) -> None:
    download = tmp_path / "Download"
    download.mkdir()
    shutil.copy2(ROOT / "Download" / "run_next.py", download / "run_next.py")
    command = download / "001_emit.py"
    command.write_text(
        "import argparse\n"
        "from pathlib import Path\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--self-test', action='store_true')\n"
        "args = parser.parse_args()\n"
        "if not args.self_test:\n"
        "    print('x' * 600000)\n"
        "    Path(__file__).with_name('001_emit_return_bundle.json').write_text('{}')\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(download / "run_next.py"), "001"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert len(completed.stdout.encode("utf-8")) <= MAX_OUTPUT_BYTES
    assert (download / "001_emit_return_bundle.json").is_file()
    assert (download / "__run_next_output.txt").stat().st_size <= MAX_OUTPUT_BYTES
    assert "TRUNCATED" in (download / "__run_next_output.txt").read_text(encoding="utf-8")
