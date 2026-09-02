from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from time import monotonic


@dataclass(frozen=True)
class AutomationLimits:
    max_turns: int = 40
    max_runtime_seconds: float = 7200.0
    max_identical_assistant_messages: int = 2
    max_identical_prompts: int = 2
    max_consecutive_errors: int = 3


@dataclass
class AutomationGuard:
    limits: AutomationLimits = field(default_factory=AutomationLimits)
    started_at: float = field(default_factory=monotonic)
    turns: int = 0
    consecutive_errors: int = 0
    _assistant_counts: dict[str, int] = field(default_factory=dict)
    _prompt_counts: dict[str, int] = field(default_factory=dict)

    @staticmethod
    def _digest(text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()

    def _check_runtime(self) -> None:
        runtime = monotonic() - self.started_at
        if runtime > self.limits.max_runtime_seconds:
            raise RuntimeError(
                f"automation runtime budget exceeded: {runtime:.1f}s"
            )

    def before_turn(self) -> None:
        self._check_runtime()
        if self.turns >= self.limits.max_turns:
            raise RuntimeError(
                f"automation turn budget exceeded: {self.turns}"
            )

    def record_assistant(self, text: str) -> None:
        self._check_runtime()
        digest = self._digest(text.strip())
        count = self._assistant_counts.get(digest, 0) + 1
        self._assistant_counts[digest] = count
        if count > self.limits.max_identical_assistant_messages:
            raise RuntimeError(
                "loop guard: identical assistant response repeated too often"
            )

    def record_prompt(self, text: str) -> None:
        self._check_runtime()
        digest = self._digest(text.strip())
        count = self._prompt_counts.get(digest, 0) + 1
        self._prompt_counts[digest] = count
        if count > self.limits.max_identical_prompts:
            raise RuntimeError(
                "loop guard: identical prompt repeated too often"
            )

    def success(self) -> None:
        self.turns += 1
        self.consecutive_errors = 0

    def error(self) -> None:
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.limits.max_consecutive_errors:
            raise RuntimeError(
                "loop guard: consecutive error budget exhausted"
            )
