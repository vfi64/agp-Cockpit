from __future__ import annotations
import json
import urllib.request
from agp_cockpit.adapters.macos_settings import bridge_token_path

DEFAULT_BASE_URL = "http://127.0.0.1:9876"

def _request(path: str, *, payload: dict | None = None, base_url: str = DEFAULT_BASE_URL) -> dict:
    token = bridge_token_path().read_text(encoding="utf-8").strip()
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"X-AGP-Token": token}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        base_url + path,
        data=data,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))

def create_live_full_auto(*, title: str, mission_text: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    return _request(
        "/v1/mission",
        payload={
            "title": title,
            "mission_text": mission_text,
            "execution_mode": "LIVE",
            "run_mode": "FULL_AUTO",
        },
        base_url=base_url,
    )

def status(*, base_url: str = DEFAULT_BASE_URL) -> dict:
    return _request("/v1/status", base_url=base_url)
