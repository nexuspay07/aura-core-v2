"""Deterministic prompt assembly independent of any AI SDK."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptBuilder:
    system_prompt: str = ""
    sections: dict[str, Any] = field(default_factory=dict)

    def add(self, name: str, value: Any) -> "PromptBuilder":
        if value not in (None, "", [], {}): self.sections[name] = value
        return self

    def build(self) -> str:
        parts = [self.system_prompt.strip()] if self.system_prompt.strip() else []
        for name in sorted(self.sections): parts.append(f"{name.replace('_', ' ').title()}:\n{self.sections[name]}")
        return "\n\n".join(parts)
