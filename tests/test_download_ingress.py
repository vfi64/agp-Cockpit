import pytest

from agp_cockpit.core.download_ingress import read_downloaded_command


def valid_command(label: str) -> str:
    return (
        "import argparse\nfrom pathlib import Path\n"
        f'COMMAND = ["agentic-kit", "{label}"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n"
        "    parser = argparse.ArgumentParser()\n"
        '    parser.add_argument("--self-test", action="store_true")\n'
        "    parser.parse_args()\n"
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def test_read_downloaded_command_accepts_repository_download(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    path = download / "1464_chat_switch_standard_task.py"
    content = valid_command("ok")
    path.write_text(content, encoding="utf-8")

    assert read_downloaded_command(path, path.name, tmp_path) == (
        path.name,
        content,
        "text/x-python",
    )


def test_read_downloaded_command_accepts_chrome_duplicate_name(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    path = download / "1464_chat_switch_standard_task (1).py"
    content = valid_command("retry")
    path.write_text(content, encoding="utf-8")

    assert read_downloaded_command(
        path,
        "1464_chat_switch_standard_task.py",
        tmp_path,
    )[1] == content


def test_read_downloaded_command_rejects_untrusted_path(tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("print('no')\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside"):
        read_downloaded_command(outside, outside.name, tmp_path)


def test_read_downloaded_command_rejects_filename_mismatch(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    path = download / "1464_chat_switch_standard_task.py"
    path.write_text("print('no')\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        read_downloaded_command(path, "1465_chat_switch_standard_task.py", tmp_path)


def test_download_name_matching_is_exact_or_numbered_duplicate():
    from agp_cockpit.core.download_ingress import _matches_download_name

    expected = "1469_chat_switch_standard_task.py"
    assert _matches_download_name(expected, expected)
    assert _matches_download_name("1469_chat_switch_standard_task (1).py", expected)
    # Observed live on 2026-09-28: "~/Downloads/1469_chat_switch_standard_task(2).py".
    assert _matches_download_name("1469_chat_switch_standard_task(2).py", expected)
    assert not _matches_download_name("1469_chat_switch_standard_task_evil.py", expected)
    assert not _matches_download_name("1469_chat_switch_standard_task (x).py", expected)


def test_background_download_name_matching_agrees_with_ingress():
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required")
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parents[1]
    script = (
        "const fs=require('fs'),vm=require('vm');"
        "const c={console,importScripts(){},setTimeout,chrome:{storage:{session:{}},downloads:{},"
        "runtime:{onMessage:{addListener(){}}},alarms:{create(){},onAlarm:{addListener(){}}},tabs:{}}};"
        "vm.createContext(c);vm.runInContext(fs.readFileSync('chrome_extension/background.js','utf8'),c);"
        "const f=c.k07DownloadNameMatches,e='1469_chat_switch_standard_task.py';"
        "const got=[f('/u/'+e,e),f('/u/1469_chat_switch_standard_task (1).py',e),"
        "f('/u/1469_chat_switch_standard_task(2).py',e),f('/u/1469_chat_switch_standard_task_evil.py',e),"
        "f('/u/1469_chat_switch_standard_task (x).py',e)];"
        "if(JSON.stringify(got)!=='[true,true,true,false,false]'){console.error(got);process.exit(1)}"
    )
    result = subprocess.run(
        [node, "-e", script], cwd=root, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
