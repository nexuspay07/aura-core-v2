"""Compatibility facade; strategic generation no longer imports an LLM SDK directly."""

from app.platform.ai import AIRequest
from app.platform.bootstrap import ai_orchestrator
from app.platform.prompting import PromptBuilder


async def generate_strategic_intelligence(prompt: str) -> str:
    request = AIRequest(
        prompt=PromptBuilder(
            system_prompt="Aura Strategic Intelligence produces deterministic platform-ready analysis."
        ).add("executive_goal", prompt).build(),
        metadata={"capability": "strategic_intelligence"},
    )
    return ai_orchestrator.generate(request, providers=["deterministic"]).content
