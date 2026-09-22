import pytest

from agp_cockpit.core.download_ingress import read_downloaded_command


def test_read_downloaded_command_accepts_repository_download(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    path = download / "1464_chat_switch_standard_task.py"
    path.write_text("print('ok')\n", encoding="utf-8")

    assert read_downloaded_command(path, path.name, tmp_path) == (
        path.name,
        "print('ok')\n",
        "text/x-python",
    )


def test_read_downloaded_command_accepts_chrome_duplicate_name(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    path = download / "1464_chat_switch_standard_task (1).py"
    path.write_text("print('retry')\n", encoding="utf-8")

    assert read_downloaded_command(
        path,
        "1464_chat_switch_standard_task.py",
        tmp_path,
    )[1] == "print('retry')\n"


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
