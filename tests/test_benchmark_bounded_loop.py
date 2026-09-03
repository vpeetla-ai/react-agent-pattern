"""Fast pytest coverage for the bounded-loop safety benchmark.

Runs a real subset of `scripts/benchmark_bounded_loop.py`'s scenarios (one
per category, plus the two boundary cases) through the real `ReActAgent`
loop and asserts real invariants about bounded vs unbounded behavior. This
is not a mock of the benchmark — it imports and executes the same
`run_trial` function the benchmark script uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from benchmark_bounded_loop import (  # noqa: E402
    BOUNDED_MAX_STEPS,
    SCENARIOS,
    UNBOUNDED_MAX_STEPS,
    run_trial,
)

SCENARIOS_BY_ID = {s.id: s for s in SCENARIOS}


def test_bounded_mode_never_exceeds_max_steps() -> None:
    for scenario in SCENARIOS:
        result = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
        assert result.steps_used <= BOUNDED_MAX_STEPS, (
            f"{scenario.id}: bounded mode used {result.steps_used} steps, "
            f"exceeding max_steps={BOUNDED_MAX_STEPS}"
        )


def test_unbounded_mode_never_exceeds_its_own_cap() -> None:
    for scenario in SCENARIOS:
        result = run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded")
        assert result.steps_used <= UNBOUNDED_MAX_STEPS


def test_quick_success_scenarios_succeed_in_both_modes() -> None:
    quick_ids = [
        "quick_calc",
        "kb_react",
        "kb_reflection",
        "kb_plan_execute",
        "immediate_answer",
        "calc_then_kb",
        "kb_then_calc",
        "three_tool_chain",
        "boundary_fits_bounded_budget",
    ]
    for scenario_id in quick_ids:
        scenario = SCENARIOS_BY_ID[scenario_id]
        bounded = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
        unbounded = run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded")
        assert bounded.succeeded, f"{scenario_id}: expected bounded success, got {bounded}"
        assert unbounded.succeeded, f"{scenario_id}: expected unbounded success, got {unbounded}"


def test_runaway_scenarios_fail_safe_under_bounded_mode() -> None:
    runaway_ids = ["runaway_calculator_only", "runaway_knowledge_base_only", "runaway_alternating_tools"]
    for scenario_id in runaway_ids:
        scenario = SCENARIOS_BY_ID[scenario_id]
        result = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
        assert not result.succeeded, f"{scenario_id}: runaway scenario unexpectedly succeeded under bounded mode"
        assert result.steps_used == BOUNDED_MAX_STEPS
        assert result.error is None
        assert result.final_answer == "Unable to complete safely within the configured step budget."


def test_runaway_scenarios_burn_far_more_steps_when_unbounded() -> None:
    scenario = SCENARIOS_BY_ID["runaway_calculator_only"]
    bounded = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
    unbounded = run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded")
    assert bounded.steps_used == BOUNDED_MAX_STEPS
    assert unbounded.steps_used == UNBOUNDED_MAX_STEPS
    assert unbounded.steps_used > bounded.steps_used
    assert not unbounded.succeeded  # still force-stopped at the 200-step cap, just later


def test_exceeds_bounded_budget_scenario_shows_real_bounded_vs_unbounded_gap() -> None:
    """A real, finite task (needs 7 model.decide() calls to finish) that the
    bounded budget (5) cannot fit, but the unbounded cap (200) can."""
    scenario = SCENARIOS_BY_ID["exceeds_bounded_budget"]
    bounded = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
    unbounded = run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded")
    assert not bounded.succeeded
    assert bounded.steps_used == BOUNDED_MAX_STEPS
    assert unbounded.succeeded
    assert unbounded.steps_used == 7


def test_malformed_tool_call_fails_identically_regardless_of_step_budget() -> None:
    scenario = SCENARIOS_BY_ID["malformed_tool_arguments"]
    bounded = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
    unbounded = run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded")
    assert not bounded.succeeded and not unbounded.succeeded
    assert bounded.steps_used == 1 and unbounded.steps_used == 1
    assert bounded.tool_calls == 0  # required-argument check fails before the handler runs
    assert bounded.error is not None and "expression" in bounded.error
    assert bounded.error == unbounded.error


def test_no_action_no_final_answer_raises_regardless_of_step_budget() -> None:
    scenario = SCENARIOS_BY_ID["model_returns_neither_action_nor_final"]
    bounded = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
    unbounded = run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded")
    assert not bounded.succeeded and not unbounded.succeeded
    assert bounded.steps_used == 1 and unbounded.steps_used == 1
    assert bounded.error == "RuntimeError: Model returned neither action nor final answer"
    assert bounded.error == unbounded.error


def test_at_least_ten_scenarios_with_required_category_coverage() -> None:
    assert len(SCENARIOS) >= 10
    categories = {s.category for s in SCENARIOS}
    assert {"success", "runaway", "adversarial"} <= categories
    assert sum(1 for s in SCENARIOS if s.category == "runaway") >= 2
    assert sum(1 for s in SCENARIOS if s.category == "adversarial") >= 1
