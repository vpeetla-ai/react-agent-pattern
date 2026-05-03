from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelDecision:
    thought: str
    action: str | None = None
    arguments: dict[str, Any] | None = None
    final_answer: str | None = None


class ReasoningModel(Protocol):
    def decide(
        self,
        user_input: str,
        tool_descriptions: list[dict[str, str]],
        observations: list[str],
    ) -> ModelDecision:
        """Return the next reasoning step, action, or final answer."""


class ScriptedReasoningModel:
    """Deterministic model stub for local testing and architecture demos."""

    def decide(
        self,
        user_input: str,
        tool_descriptions: list[dict[str, str]],
        observations: list[str],
    ) -> ModelDecision:
        normalized = user_input.lower()
        if observations:
            return ModelDecision(
                thought="I have enough grounded evidence from the tool.",
                final_answer=f"Grounded answer: {observations[-1]}",
            )
        if "calculate" in normalized or any(char.isdigit() for char in normalized):
            expression = "".join(char for char in user_input if char in "0123456789+-*/(). ")
            return ModelDecision(
                thought="The user needs arithmetic, so I should use the calculator.",
                action="calculator",
                arguments={"expression": expression.strip()},
            )
        return ModelDecision(
            thought="The user is asking for architecture knowledge.",
            action="knowledge_base",
            arguments={"query": "react"},
        )

