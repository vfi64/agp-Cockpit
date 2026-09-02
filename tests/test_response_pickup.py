import json

import pytest

from agp_cockpit.core.response_pickup import (
    clipboard_changed,
    extract_work_order_from_response,
    snapshot_text,
)


def test_clipboard_change_detection():
    before = snapshot_text("old")
    assert clipboard_changed(before, "new") is True
    assert clipboard_changed(before, "old") is False


def test_extract_pure_json_work_order():
    text = json.dumps({
        "kind": "generic",
        "cwd": "/tmp",
        "argv": ["/usr/bin/printf", "x"],
    })

    result = extract_work_order_from_response(text)

    assert result.extraction_kind == "pure-json"
    assert result.work_order_text is not None


def test_extract_single_fenced_json_work_order():
    text = '''
Führe als Nächstes diesen Auftrag aus:

```json
{
  "kind": "generic",
  "cwd": "/tmp",
  "argv": ["/usr/bin/printf", "x"]
}
```
'''

    result = extract_work_order_from_response(text)

    assert result.extraction_kind == "fenced-json"
    assert result.work_order_text is not None


def test_prose_without_order_is_preserved_but_not_executable():
    result = extract_work_order_from_response(
        "Alles erledigt. Kein weiterer Auftrag."
    )

    assert result.extraction_kind == "prose-only"
    assert result.work_order_text is None


def test_multiple_work_orders_fail_closed():
    text = '''
```json
{"cwd":"/tmp","argv":["echo","a"]}
```

```json
{"cwd":"/tmp","argv":["echo","b"]}
```
'''

    with pytest.raises(ValueError):
        extract_work_order_from_response(text)
