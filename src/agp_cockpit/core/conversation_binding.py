"""One ChatGPT conversation per repository (plan P4, AGP_CONVERSATION_BINDING_V1).

A chat carries the command digest, the work-order history and the repository
facts of one repository. After a repository switch the same chat must not
continue with another repository. The binding lives in the global bridge
runtime root (``conversation-bindings.json``): a conversation id is bound to
the repository of the first standard task started in it, and a later start
from a chat bound to another repository is blocked with a clear message.
A fresh chat (``https://chatgpt.com/`` without ``/c/<id>``) has no id yet and
is bound once its id is known (next start or a verified DONE).
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

FILE = "conversation-bindings.json"


def conversation_id(url: str) -> str:
    parts = [part for part in urlparse(str(url or "")).path.split("/") if part]
    return parts[1] if len(parts) >= 2 and parts[0] == "c" else ""


class ConversationBindingStore:
    def __init__(self, runtime_root: Path) -> None:
        self.path = Path(runtime_root) / FILE

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def owner(self, url: str) -> str | None:
        cid = conversation_id(url)
        return self._load().get(cid) if cid else None

    def bind(self, url: str, repository_root: Path) -> bool:
        """Bind an unbound conversation; never rebinds. True when bound now."""
        cid = conversation_id(url)
        if not cid:
            return False
        data = self._load()
        if cid in data:
            return False
        data[cid] = str(Path(repository_root).expanduser().resolve())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return True

    def block_reason(self, url: str, repository_root: Path) -> str | None:
        owner = self.owner(url)
        current = str(Path(repository_root).expanduser().resolve())
        if owner and owner != current:
            return (f"Dieser ChatGPT-Chat gehört zum Repository {owner}. Für {current} bitte einen "
                    "neuen Chat öffnen (Repo-Wechsel, P4).")
        return None
