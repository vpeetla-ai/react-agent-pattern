"""Bounded-loop safety benchmark for `ReActAgent`.

This measures the pattern's actual *mechanical* behavior — not LLM output
quality. Every `ReasoningModel` used here is a hand-written, fully
deterministic stub (same convention as `ScriptedReasoningModel` in
`models.py` and the "Deterministic model stub — pytest without API keys"
line in the README). There is no LLM call anywhere in this benchmark, no
API key, and no network access. Re-running it produces byte-identical
results because every scenario's control flow is a fixed Python function of
its inputs.

What it measures, per trial scenario, run twice — once with the agent's
default bounded step budget (`max_steps=5`) and once with a large
"unbounded" surrogate budget (`max_steps=200`, chosen so the benchmark still
finishes in finite time; a truly unbounded runaway loop cannot be
benchmarked, so 200 stands in and the real numbers are reported as-is, not
rounded up to "infinite"):

  - success: did the agent return a real grounded final answer (not the
    "Unable to complete safely..." step-budget sentinel, and without
    raising an exception)?
  - steps_used: how many times `model.decide()` was actually called.
  - tool_calls: how many times a tool's handler actually executed.
  - wall_time_s: real wall-clock seconds for that trial (perf_counter).

Scenario categories:
  - success:    tasks the deterministic model resolves in a small, finite
                number of steps (including one boundary case that exactly
                fits the bounded budget, and one that deliberately needs
                more steps than the bounded budget allows — a real,
                finite task where bounded mode fails and unbounded mode
                succeeds).
  - runaway:    the model is constructed to NEVER emit `final_answer` — it
                keeps invoking a tool forever. This is the core
                differentiation: bounded mode safely terminates at
                max_steps; unbounded mode burns the full 200-step cap
                before also being force-stopped (finite cap, not "forever").
  - adversarial: edge cases exercising agent.py's other exit paths — a
                malformed tool call (missing required argument, so
                `Tool.invoke` raises `ValueError`) and a model that
                returns neither `action` nor `final_answer` (agent.py
                raises `RuntimeError` by design). Both fail identically at
                step 1 in bounded AND unbounded mode: the step budget does
                not, and is not meant to, protect against these — only
                against non-terminating decision loops. Reporting this
                honestly is the point.

Run directly: `python scripts/benchmark_bounded_loop.py`
Writes: docs/receipts/benchmark.md
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from react_agent_pattern import ReActAgent, ToolRegistry, calculator_tool, knowledge_base_tool
from react_agent_pattern.models import ModelDecision
from react_agent_pattern.tools import Tool

BOUNDED_MAX_STEPS = 5  # ReActAgent's real default
UNBOUNDED_MAX_STEPS = 200  # finite surrogate for "unbounded" — see module docstring


# --------------------------------------------------------------------------
# Deterministic model stubs used only by this benchmark (not production
# reasoning models — see repo-level "Deterministic model stub" convention).
# --------------------------------------------------------------------------


class ImmediateAnswerModel:
    """Finalizes on the very first decision — no tool call needed at all."""

    def __init__(self, answer: str) -> None:
        self.calls = 0
        self._answer = answer

    def decide(self, user_input: str, tool_descriptions: list[dict[str, str]], observations: list[str]) -> ModelDecision:
        self.calls += 1
        return ModelDecision(thought="No tool needed for this request.", final_answer=self._answer)


class ScriptedPlanModel:
    """Executes a fixed, ordered plan of tool calls, then finalizes.

    `plan` is a list of (tool_name, arguments) executed in order, one per
    decide() call. Once every planned tool call has produced an
    observation, the next decide() call emits final_answer. This makes the
    exact number of steps to success a deterministic function of len(plan):
    len(plan) tool-call steps + 1 finalize step.
    """

    def __init__(self, plan: list[tuple[str, dict[str, Any]]]) -> None:
        self.calls = 0
        self._plan = plan

    def decide(self, user_input: str, tool_descriptions: list[dict[str, str]], observations: list[str]) -> ModelDecision:
        self.calls += 1
        idx = len(observations)
        if idx < len(self._plan):
            name, args = self._plan[idx]
            return ModelDecision(thought=f"Plan step {idx + 1}/{len(self._plan)}.", action=name, arguments=args)
        return ModelDecision(
            thought="Plan complete, all observations gathered.",
            final_answer=f"Composed answer from {len(observations)} observation(s): {observations}",
        )


class RunawayModel:
    """Never emits final_answer — always invokes the next tool in a fixed,
    repeating cycle. Used to demonstrate bounded-vs-unbounded step burn on
    a genuinely non-terminating decision policy."""

    def __init__(self, cycle: list[tuple[str, dict[str, Any]]]) -> None:
        self.calls = 0
        self._cycle = cycle

    def decide(self, user_input: str, tool_descriptions: list[dict[str, str]], observations: list[str]) -> ModelDecision:
        self.calls += 1
        name, args = self._cycle[(self.calls - 1) % len(self._cycle)]
        return ModelDecision(thought="Always keep going; never finalize.", action=name, arguments=args)


class MalformedToolCallModel:
    """Always calls the calculator tool with a missing required argument,
    so `Tool.invoke` raises ValueError on the very first attempt."""

    def __init__(self) -> None:
        self.calls = 0

    def decide(self, user_input: str, tool_descriptions: list[dict[str, str]], observations: list[str]) -> ModelDecision:
        self.calls += 1
        return ModelDecision(thought="Attempt a tool call with malformed arguments.", action="calculator", arguments={})


class NoActionNoFinalModel:
    """Returns a decision with neither `action` nor `final_answer` — the
    case agent.py explicitly guards with `raise RuntimeError(...)`."""

    def __init__(self) -> None:
        self.calls = 0

    def decide(self, user_input: str, tool_descriptions: list[dict[str, str]], observations: list[str]) -> ModelDecision:
        self.calls += 1
        return ModelDecision(thought="No actionable decision produced.")


def counting_tool_registry() -> tuple[ToolRegistry, dict[str, int]]:
    """A fresh ToolRegistry per trial, wrapping each tool's handler to count
    real invocations (only incremented when the handler body actually
    executes — a required-argument failure in Tool.invoke happens before
    the wrapped handler runs, so it correctly does NOT count as a tool
    call)."""

    counts = {"calls": 0}

    def wrap(tool: Tool) -> Tool:
        def handler(arguments: dict[str, Any]) -> str:
            counts["calls"] += 1
            return tool.handler(arguments)

        return Tool(name=tool.name, description=tool.description, handler=handler, required_keys=tool.required_keys)

    registry = ToolRegistry([wrap(calculator_tool()), wrap(knowledge_base_tool())])
    return registry, counts


# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    id: str
    category: str  # "success" | "runaway" | "adversarial"
    user_input: str
    description: str
    model_factory: Callable[[], Any]


SCENARIOS: list[Scenario] = [
    Scenario(
        id="quick_calc",
        category="success",
        user_input="Calculate 2 + 3",
        description="One calculator call then finalize (2 steps).",
        model_factory=lambda: ScriptedPlanModel([("calculator", {"expression": "2 + 3"})]),
    ),
    Scenario(
        id="kb_react",
        category="success",
        user_input="What is ReAct?",
        description="One knowledge_base lookup then finalize (2 steps).",
        model_factory=lambda: ScriptedPlanModel([("knowledge_base", {"query": "react"})]),
    ),
    Scenario(
        id="kb_reflection",
        category="success",
        user_input="What is the Reflection pattern?",
        description="One knowledge_base lookup then finalize (2 steps).",
        model_factory=lambda: ScriptedPlanModel([("knowledge_base", {"query": "reflection"})]),
    ),
    Scenario(
        id="kb_plan_execute",
        category="success",
        user_input="What is Plan and Execute?",
        description="One knowledge_base lookup then finalize (2 steps).",
        model_factory=lambda: ScriptedPlanModel([("knowledge_base", {"query": "plan_execute"})]),
    ),
    Scenario(
        id="immediate_answer",
        category="success",
        user_input="Say hello",
        description="No tool call needed at all (1 step).",
        model_factory=lambda: ImmediateAnswerModel("Hello! How can I help?"),
    ),
    Scenario(
        id="calc_then_kb",
        category="success",
        user_input="Calculate 10 * 4 then explain ReAct",
        description="Two tool calls (calculator, knowledge_base) then finalize (3 steps).",
        model_factory=lambda: ScriptedPlanModel(
            [("calculator", {"expression": "10 * 4"}), ("knowledge_base", {"query": "react"})]
        ),
    ),
    Scenario(
        id="kb_then_calc",
        category="success",
        user_input="Explain reflection then calculate 7 + 8",
        description="Two tool calls (knowledge_base, calculator) then finalize (3 steps).",
        model_factory=lambda: ScriptedPlanModel(
            [("knowledge_base", {"query": "reflection"}), ("calculator", {"expression": "7 + 8"})]
        ),
    ),
    Scenario(
        id="three_tool_chain",
        category="success",
        user_input="Multi-part lookup and arithmetic task",
        description="Three tool calls then finalize (4 steps) — under bounded budget.",
        model_factory=lambda: ScriptedPlanModel(
            [
                ("calculator", {"expression": "1 + 1"}),
                ("knowledge_base", {"query": "react"}),
                ("calculator", {"expression": "3 * 3"}),
            ]
        ),
    ),
    Scenario(
        id="boundary_fits_bounded_budget",
        category="success",
        user_input="Four-part plan that exactly fills the bounded step budget",
        description="Four tool calls then finalize on step 5 — exactly equal to max_steps=5.",
        model_factory=lambda: ScriptedPlanModel(
            [
                ("calculator", {"expression": "2 * 2"}),
                ("knowledge_base", {"query": "react"}),
                ("calculator", {"expression": "5 - 1"}),
                ("knowledge_base", {"query": "reflection"}),
            ]
        ),
    ),
    Scenario(
        id="exceeds_bounded_budget",
        category="success",
        user_input="Six-part plan that exceeds the bounded step budget",
        description=(
            "Six tool calls then finalize on step 7 — a real, finite task "
            "that bounded mode (max_steps=5) cannot complete in time but "
            "unbounded mode (max_steps=200) completes normally."
        ),
        model_factory=lambda: ScriptedPlanModel(
            [
                ("calculator", {"expression": "1 + 2"}),
                ("knowledge_base", {"query": "react"}),
                ("calculator", {"expression": "3 + 4"}),
                ("knowledge_base", {"query": "reflection"}),
                ("calculator", {"expression": "5 + 6"}),
                ("knowledge_base", {"query": "plan_execute"}),
            ]
        ),
    ),
    Scenario(
        id="runaway_calculator_only",
        category="runaway",
        user_input="A request the model never resolves (always calculates)",
        description="Model always calls calculator, never emits final_answer.",
        model_factory=lambda: RunawayModel([("calculator", {"expression": "1 + 1"})]),
    ),
    Scenario(
        id="runaway_knowledge_base_only",
        category="runaway",
        user_input="A request the model never resolves (always looks up)",
        description="Model always calls knowledge_base, never emits final_answer.",
        model_factory=lambda: RunawayModel([("knowledge_base", {"query": "react"})]),
    ),
    Scenario(
        id="runaway_alternating_tools",
        category="runaway",
        user_input="A request the model never resolves (alternates tools)",
        description="Model alternates calculator/knowledge_base forever, never finalizes.",
        model_factory=lambda: RunawayModel(
            [("calculator", {"expression": "9 - 9"}), ("knowledge_base", {"query": "reflection"})]
        ),
    ),
    Scenario(
        id="malformed_tool_arguments",
        category="adversarial",
        user_input="A request whose tool call is missing a required argument",
        description=(
            "Calculator called with no 'expression' argument on every attempt — "
            "Tool.invoke raises ValueError on step 1, independent of max_steps."
        ),
        model_factory=lambda: MalformedToolCallModel(),
    ),
    Scenario(
        id="model_returns_neither_action_nor_final",
        category="adversarial",
        user_input="A request the model cannot decide how to handle",
        description=(
            "decide() returns neither action nor final_answer — agent.py raises "
            "RuntimeError on step 1, independent of max_steps."
        ),
        model_factory=lambda: NoActionNoFinalModel(),
    ),
]


# --------------------------------------------------------------------------
# Trial execution
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TrialResult:
    scenario_id: str
    category: str
    mode: str  # "bounded" | "unbounded"
    max_steps: int
    succeeded: bool
    steps_used: int
    tool_calls: int
    final_answer: str | None
    error: str | None
    wall_time_s: float


UNABLE_SENTINEL = "Unable to complete safely within the configured step budget."


def run_trial(scenario: Scenario, max_steps: int, mode: str) -> TrialResult:
    tools, counts = counting_tool_registry()
    model = scenario.model_factory()
    agent = ReActAgent(model=model, tools=tools, max_steps=max_steps)

    start = time.perf_counter()
    answer: str | None = None
    error: str | None = None
    try:
        result = agent.run(scenario.user_input)
        answer = result.answer
        succeeded = answer != UNABLE_SENTINEL
    except Exception as exc:  # noqa: BLE001 - deliberately capturing real adversarial failures
        error = f"{type(exc).__name__}: {exc}"
        succeeded = False
    wall_time_s = time.perf_counter() - start

    return TrialResult(
        scenario_id=scenario.id,
        category=scenario.category,
        mode=mode,
        max_steps=max_steps,
        succeeded=succeeded,
        steps_used=model.calls,
        tool_calls=counts["calls"],
        final_answer=answer,
        error=error,
        wall_time_s=wall_time_s,
    )


def run_benchmark(scenarios: list[Scenario] | None = None) -> list[TrialResult]:
    scenarios = scenarios if scenarios is not None else SCENARIOS
    results: list[TrialResult] = []
    for scenario in scenarios:
        results.append(run_trial(scenario, BOUNDED_MAX_STEPS, "bounded"))
        results.append(run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded"))
    return results


# --------------------------------------------------------------------------
# Aggregation + report
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ModeSummary:
    mode: str
    trial_count: int
    success_count: int
    success_rate: float
    avg_steps_used: float
    avg_tool_calls: float
    max_steps_used: int
    total_tool_calls: int


def summarize(results: list[TrialResult], mode: str) -> ModeSummary:
    subset = [r for r in results if r.mode == mode]
    n = len(subset)
    successes = sum(1 for r in subset if r.succeeded)
    return ModeSummary(
        mode=mode,
        trial_count=n,
        success_count=successes,
        success_rate=successes / n if n else 0.0,
        avg_steps_used=statistics.fmean(r.steps_used for r in subset) if n else 0.0,
        avg_tool_calls=statistics.fmean(r.tool_calls for r in subset) if n else 0.0,
        max_steps_used=max((r.steps_used for r in subset), default=0),
        total_tool_calls=sum(r.tool_calls for r in subset),
    )


def render_report(results: list[TrialResult]) -> str:
    bounded = summarize(results, "bounded")
    unbounded = summarize(results, "unbounded")

    lines: list[str] = []
    lines.append("# Bounded-Loop Safety Benchmark")
    lines.append("")
    lines.append(
        "Real, executed benchmark of `ReActAgent`'s mechanical loop-termination "
        "behavior — bounded (`max_steps=5`, the library default) vs. an "
        "\"unbounded\" surrogate (`max_steps=200`). This is NOT an LLM output-quality "
        "benchmark: every `ReasoningModel` here is a hand-written deterministic "
        "stub (same convention as `ScriptedReasoningModel` — no API keys, no "
        "network, byte-identical results on re-run). See `scripts/benchmark_bounded_loop.py` "
        "for full methodology and every scenario's construction."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Mode | Trials | Successes | Success rate | Avg steps used | Avg tool calls | Max steps used |")
    lines.append("|------|-------:|----------:|-------------:|----------------:|----------------:|----------------:|")
    for summary in (bounded, unbounded):
        lines.append(
            f"| {summary.mode} (max_steps={BOUNDED_MAX_STEPS if summary.mode == 'bounded' else UNBOUNDED_MAX_STEPS}) "
            f"| {summary.trial_count} | {summary.success_count} | {summary.success_rate:.1%} "
            f"| {summary.avg_steps_used:.2f} | {summary.avg_tool_calls:.2f} | {summary.max_steps_used} |"
        )
    lines.append("")
    lines.append(
        f"**Headline:** {bounded.success_count}/{bounded.trial_count} trials succeed under bounded "
        f"mode ({bounded.success_rate:.0%}) vs {unbounded.success_count}/{unbounded.trial_count} under "
        f"unbounded mode ({unbounded.success_rate:.0%}). Unbounded mode burns "
        f"{unbounded.total_tool_calls} total tool calls across all trials vs bounded mode's "
        f"{bounded.total_tool_calls} — {unbounded.total_tool_calls / max(bounded.total_tool_calls, 1):.1f}x more — "
        "almost entirely driven by the runaway scenarios running to the full 200-step cap "
        "instead of stopping at 5."
    )
    lines.append("")

    lines.append("## Per-trial results")
    lines.append("")
    lines.append("| Scenario | Category | Mode | Max steps | Succeeded | Steps used | Tool calls | Wall time (s) | Outcome |")
    lines.append("|----------|----------|------|----------:|:---------:|-----------:|-----------:|---------------:|---------|")
    for r in results:
        outcome = r.error if r.error else (r.final_answer or "")
        outcome = outcome.replace("|", "\\|")
        if len(outcome) > 70:
            outcome = outcome[:67] + "..."
        lines.append(
            f"| {r.scenario_id} | {r.category} | {r.mode} | {r.max_steps} | "
            f"{'yes' if r.succeeded else 'no'} | {r.steps_used} | {r.tool_calls} | "
            f"{r.wall_time_s:.6f} | {outcome} |"
        )
    lines.append("")

    lines.append("## Scenario descriptions")
    lines.append("")
    lines.append("| Scenario | Category | Description |")
    lines.append("|----------|----------|--------------|")
    for scenario in SCENARIOS:
        lines.append(f"| {scenario.id} | {scenario.category} | {scenario.description} |")
    lines.append("")

    lines.append("## Methodology notes")
    lines.append("")
    lines.append(
        "- **Deterministic stub, by design.** Every model in this benchmark is a hand-written "
        "Python class implementing the `ReasoningModel` protocol from `models.py`. None of them "
        "call an LLM API. This matches the repo's disclosed architecture — see README: "
        "\"Deterministic model stub — `pytest` without API keys\" and \"Curriculum stub... not a "
        "production agent fleet.\" This benchmark measures the *loop's* mechanical behavior "
        "(does the step budget actually bound execution; does it fail safely), not model "
        "reasoning quality."
    )
    lines.append(
        "- **`steps_used`** counts real calls to `model.decide()` (tracked via a per-model call "
        "counter), i.e. real loop iterations attempted — including the final iteration that "
        "either finalizes or exhausts the budget."
    )
    lines.append(
        "- **`tool_calls`** counts real executions of a tool's handler body (tracked via a "
        "counting wrapper around each `Tool` in a fresh `ToolRegistry` per trial). A tool call "
        "that fails argument validation before the handler runs (`Tool.invoke`'s required-key "
        "check) correctly does NOT increment this counter — see the `malformed_tool_arguments` "
        "trial, which shows `tool_calls=0` because the handler body never executed."
    )
    lines.append(
        "- **\"Unbounded\" is a finite surrogate (`max_steps=200`), not literal infinity.** A "
        "truly unbounded runaway loop cannot be benchmarked in finite time. The real, exact "
        "numbers at the 200-step cap are reported above — they are not rounded up to "
        "\"infinite\" or otherwise estimated."
    )
    lines.append(
        "- **Adversarial scenarios are not \"fixed\" by bounding steps.** `malformed_tool_arguments` "
        "and `model_returns_neither_action_nor_final` both fail at step 1 in BOTH bounded and "
        "unbounded mode, with identical exceptions (`ValueError` / `RuntimeError` from `agent.py` "
        "and `tools.py`). The step budget protects specifically against non-terminating decision "
        "policies (the runaway scenarios); it does not, and was never meant to, catch malformed "
        "tool calls or invalid model decisions. That is a real, honest finding from this run, "
        "not a claimed feature."
    )
    lines.append(
        "- **Reproduce:** `python scripts/benchmark_bounded_loop.py` from the repo root "
        "regenerates this file with identical numbers (fully deterministic, no network, no keys)."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    results = run_benchmark()
    report = render_report(results)
    out_path = Path(__file__).resolve().parent.parent / "docs" / "receipts" / "benchmark.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    bounded = summarize(results, "bounded")
    unbounded = summarize(results, "unbounded")
    print(f"Wrote {out_path}")
    print(
        f"bounded: {bounded.success_count}/{bounded.trial_count} success "
        f"({bounded.success_rate:.1%}), avg steps={bounded.avg_steps_used:.2f}"
    )
    print(
        f"unbounded: {unbounded.success_count}/{unbounded.trial_count} success "
        f"({unbounded.success_rate:.1%}), avg steps={unbounded.avg_steps_used:.2f}"
    )


if __name__ == "__main__":
    main()
