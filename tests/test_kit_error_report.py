import json

from agp_cockpit.core.kit_error_report import (
    KitErrorEvidence,
    build_kit_error_report,
    write_kit_error_report,
)


def test_report_writes_json_and_markdown(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    report = build_kit_error_report(
        repository_root=repo,
        classification="GREENFIELD_DEFECT",
        title="Example",
        summary="Summary",
        workflow_phase="bootstrap",
        expected_behavior="pass",
        observed_behavior="blocked",
        reproduction_steps=["run command"],
        evidence=[
            KitErrorEvidence(
                command=["agentic-kit", "work", "start"],
                returncode=2,
                stdout="STATE=BLOCKED",
                stderr="",
            )
        ],
        suspected_component="work-start",
    )

    json_path, md_path = write_kit_error_report(
        report,
        output_root=tmp_path / "reports",
    )

    data = json.loads(json_path.read_text())
    assert data["classification"] == "GREENFIELD_DEFECT"
    assert "STATE=BLOCKED" in md_path.read_text()
