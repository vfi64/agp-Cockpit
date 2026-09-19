from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrowserTurnRequest:
    conversation_url: str
    assistant_text: str
    turn_id: str


@dataclass(frozen=True)
class BrowserTurnResponse:
    action: str
    prompt: str
    state: str
    note: str = ""


def parse_turn_request(text: str) -> BrowserTurnRequest:
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise TypeError("request must be a JSON object")

    conversation_url = data.get("conversation_url")
    assistant_text = data.get("assistant_text")
    turn_id = data.get("turn_id")

    if (
        not isinstance(conversation_url, str)
        or not conversation_url.startswith("https://chatgpt.com/")
    ):
        raise ValueError("conversation_url must be an https://chatgpt.com/ URL")
    if not isinstance(assistant_text, str) or not assistant_text.strip():
        raise ValueError("assistant_text must be non-empty")
    if not isinstance(turn_id, str) or not turn_id.strip():
        raise ValueError("turn_id must be non-empty")

    return BrowserTurnRequest(
        conversation_url=conversation_url,
        assistant_text=assistant_text,
        turn_id=turn_id,
    )


def encode_turn_response(response: BrowserTurnResponse) -> str:
    return json.dumps(
        {
            "action": response.action,
            "prompt": response.prompt,
            "state": response.state,
            "note": response.note,
        },
        ensure_ascii=False,
    )
