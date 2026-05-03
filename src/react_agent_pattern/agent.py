from dataclasses import dataclass

from .models import ReasoningModel
from .tools import ToolRegistry
from .tracing import Trace


@dataclass(frozen=True)
class ReActResult:
    answer: str
    trace: Trace
    observations: list[str]


class ReActAgent:
    def __init__(
        self,
        model: ReasoningModel,
        tools: ToolRegistry,
        max_steps: int = 5,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.model = model
        self.tools = tools
        self.max_steps = max_steps

    def run(self, user_input: str) -> ReActResult:
        trace = Trace()
        observations: list[str] = []
        trace.add("request.received", user_input=user_input)

        for step in range(1, self.max_steps + 1):
            decision = self.model.decide(user_input, self.tools.descriptions(), observations)
            trace.add(
                "model.decision",
                step=step,
                thought=decision.thought,
                action=decision.action,
                final_answer=decision.final_answer,
            )
            if decision.final_answer:
                trace.add("request.completed", step=step)
                return ReActResult(decision.final_answer, trace, observations)
            if not decision.action:
                raise RuntimeError("Model returned neither action nor final answer")

            tool = self.tools.get(decision.action)
            observation = tool.invoke(decision.arguments or {})
            observations.append(observation)
            trace.add("tool.observation", step=step, tool=tool.name, observation=observation)

        trace.add("request.stopped", reason="max_steps_exceeded")
        return ReActResult(
            "Unable to complete safely within the configured step budget.",
            trace,
            observations,
        )

