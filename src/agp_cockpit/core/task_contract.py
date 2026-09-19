from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

VALID_EFFECT_CLASSES=frozenset({"E0","E1","E2","E3","E4"})
@dataclass(frozen=True)
class LocalTaskContract:
    repository_root: Path
    allowed_effects: frozenset[str]=frozenset()
    allowed_tools: frozenset[str]=frozenset()
    allow_network: bool=False
    def __post_init__(self):
        object.__setattr__(self,"repository_root",self.repository_root.expanduser().resolve())
        effects=frozenset(str(x).upper() for x in self.allowed_effects)
        unknown=effects-VALID_EFFECT_CLASSES
        if unknown: raise ValueError(f"unsupported effect classes: {sorted(unknown)}")
        object.__setattr__(self,"allowed_effects",effects)
        object.__setattr__(self,"allowed_tools",frozenset(str(x) for x in self.allowed_tools if str(x)))
    def allows(self,*,effect:str,tool:str)->bool:
        return effect.upper() in self.allowed_effects and tool in self.allowed_tools
