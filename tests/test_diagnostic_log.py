import json

from agp_cockpit.core.diagnostic_log import (
    DiagnosticLogConfig,
    DiagnosticLogger,
)


def test_diagnostic_log_writes_json_and_rotates(tmp_path):
    logger = DiagnosticLogger(
        tmp_path,
        config=DiagnosticLogConfig(
            max_bytes=300,
            backup_count=2,
        ),
    )

    for i in range(30):
        logger.event(
            "TEST_EVENT",
            mission_id="m1",
            turn=i,
            details={"value": "x" * 40},
        )

    assert logger.log_path.exists()
    lines = logger.log_path.read_text(
        encoding="utf-8"
    ).splitlines()

    if lines:
        payload = json.loads(lines[-1])
        assert payload["event"] == "TEST_EVENT"
        assert payload["application_version"]
        assert payload["bridge_build_id"]
        assert payload["bridge_protocol_version"] == 1
        assert payload["timestamp_utc"].endswith("+00:00")

    backups = list(
        logger.log_root.glob("bridge.log.*")
    )
    assert len(backups) <= 2


def test_text_meta_does_not_store_full_text(tmp_path):
    meta = DiagnosticLogger.text_meta(
        "secret-" + ("x" * 500)
    )

    assert meta["chars"] == 507
    assert len(meta["preview"]) <= 160
    assert meta["sha256"]
