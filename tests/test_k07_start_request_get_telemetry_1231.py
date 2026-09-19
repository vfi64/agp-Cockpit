from pathlib import Path


def test_poll_event():
 s=Path('src/agp_cockpit/core/bridge_server.py').read_text(); assert 'TASK_START_REQUEST_POLLED' in s and 'request_mission_id' in s and 'request_task_id' in s
