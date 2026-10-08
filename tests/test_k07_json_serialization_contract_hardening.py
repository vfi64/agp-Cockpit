from pathlib import Path

C = Path("chrome_extension/content.js").read_text()


def test_bootstrap_demands_json_parseable_serialization():
    assert "must be parseable by JSON.parse" in C
    assert "Escape every double quote inside JSON string values using the standard JSON backslash escape" in C
    # AGP_LEGACY_PATHS_REMOVED_V1: the "JSON-like text" sentence and the /bin/sh quoting example were
    # part of the 061 LIVE probe mission text, which is gone with the probe.


def test_format_repair_targets_serialization_not_semantics():
    assert "JSON syntax invalid; likely an unescaped quote or other string-escaping error" in C
    assert "Re-serialize the SAME intended work order" in C
    assert "Preserve semantics, not broken byte-for-byte string serialization" in C
    assert "Escape every double quote inside JSON string values using the standard JSON backslash escape" in C
    assert "No Markdown fences, no commentary" in C
