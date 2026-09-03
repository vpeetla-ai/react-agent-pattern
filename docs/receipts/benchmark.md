# Bounded-Loop Safety Benchmark

Real, executed benchmark of `ReActAgent`'s mechanical loop-termination behavior — bounded (`max_steps=5`, the library default) vs. an "unbounded" surrogate (`max_steps=200`). This is NOT an LLM output-quality benchmark: every `ReasoningModel` here is a hand-written deterministic stub (same convention as `ScriptedReasoningModel` — no API keys, no network, byte-identical results on re-run). See `scripts/benchmark_bounded_loop.py` for full methodology and every scenario's construction.

## Summary

| Mode | Trials | Successes | Success rate | Avg steps used | Avg tool calls | Max steps used |
|------|-------:|----------:|-------------:|----------------:|----------------:|----------------:|
| bounded (max_steps=5) | 15 | 9 | 60.0% | 3.07 | 2.33 | 5 |
| unbounded (max_steps=200) | 15 | 10 | 66.7% | 42.20 | 41.40 | 200 |

**Headline:** 9/15 trials succeed under bounded mode (60%) vs 10/15 under unbounded mode (67%). Unbounded mode burns 621 total tool calls across all trials vs bounded mode's 35 — 17.7x more — almost entirely driven by the runaway scenarios running to the full 200-step cap instead of stopping at 5.

## Per-trial results

| Scenario | Category | Mode | Max steps | Succeeded | Steps used | Tool calls | Wall time (s) | Outcome |
|----------|----------|------|----------:|:---------:|-----------:|-----------:|---------------:|---------|
| quick_calc | success | bounded | 5 | yes | 2 | 1 | 0.000078 | Composed answer from 1 observation(s): ['5'] |
| quick_calc | success | unbounded | 200 | yes | 2 | 1 | 0.000048 | Composed answer from 1 observation(s): ['5'] |
| kb_react | success | bounded | 5 | yes | 2 | 1 | 0.000050 | Composed answer from 1 observation(s): ['ReAct alternates reasoning... |
| kb_react | success | unbounded | 200 | yes | 2 | 1 | 0.000041 | Composed answer from 1 observation(s): ['ReAct alternates reasoning... |
| kb_reflection | success | bounded | 5 | yes | 2 | 1 | 0.000020 | Composed answer from 1 observation(s): ['Reflection adds critique a... |
| kb_reflection | success | unbounded | 200 | yes | 2 | 1 | 0.000019 | Composed answer from 1 observation(s): ['Reflection adds critique a... |
| kb_plan_execute | success | bounded | 5 | yes | 2 | 1 | 0.000018 | Composed answer from 1 observation(s): ['Plan and Execute separates... |
| kb_plan_execute | success | unbounded | 200 | yes | 2 | 1 | 0.000018 | Composed answer from 1 observation(s): ['Plan and Execute separates... |
| immediate_answer | success | bounded | 5 | yes | 1 | 0 | 0.000013 | Hello! How can I help? |
| immediate_answer | success | unbounded | 200 | yes | 1 | 0 | 0.000013 | Hello! How can I help? |
| calc_then_kb | success | bounded | 5 | yes | 3 | 2 | 0.000044 | Composed answer from 2 observation(s): ['40', 'ReAct alternates rea... |
| calc_then_kb | success | unbounded | 200 | yes | 3 | 2 | 0.000047 | Composed answer from 2 observation(s): ['40', 'ReAct alternates rea... |
| kb_then_calc | success | bounded | 5 | yes | 3 | 2 | 0.000040 | Composed answer from 2 observation(s): ['Reflection adds critique a... |
| kb_then_calc | success | unbounded | 200 | yes | 3 | 2 | 0.000038 | Composed answer from 2 observation(s): ['Reflection adds critique a... |
| three_tool_chain | success | bounded | 5 | yes | 4 | 3 | 0.000054 | Composed answer from 3 observation(s): ['2', 'ReAct alternates reas... |
| three_tool_chain | success | unbounded | 200 | yes | 4 | 3 | 0.000052 | Composed answer from 3 observation(s): ['2', 'ReAct alternates reas... |
| boundary_fits_bounded_budget | success | bounded | 5 | yes | 5 | 4 | 0.000057 | Composed answer from 4 observation(s): ['4', 'ReAct alternates reas... |
| boundary_fits_bounded_budget | success | unbounded | 200 | yes | 5 | 4 | 0.000066 | Composed answer from 4 observation(s): ['4', 'ReAct alternates reas... |
| exceeds_bounded_budget | success | bounded | 5 | no | 5 | 5 | 0.000067 | Unable to complete safely within the configured step budget. |
| exceeds_bounded_budget | success | unbounded | 200 | yes | 7 | 6 | 0.000076 | Composed answer from 6 observation(s): ['3', 'ReAct alternates reas... |
| runaway_calculator_only | runaway | bounded | 5 | no | 5 | 5 | 0.000087 | Unable to complete safely within the configured step budget. |
| runaway_calculator_only | runaway | unbounded | 200 | no | 200 | 200 | 0.002659 | Unable to complete safely within the configured step budget. |
| runaway_knowledge_base_only | runaway | bounded | 5 | no | 5 | 5 | 0.000039 | Unable to complete safely within the configured step budget. |
| runaway_knowledge_base_only | runaway | unbounded | 200 | no | 200 | 200 | 0.000736 | Unable to complete safely within the configured step budget. |
| runaway_alternating_tools | runaway | bounded | 5 | no | 5 | 5 | 0.000069 | Unable to complete safely within the configured step budget. |
| runaway_alternating_tools | runaway | unbounded | 200 | no | 200 | 200 | 0.003260 | Unable to complete safely within the configured step budget. |
| malformed_tool_arguments | adversarial | bounded | 5 | no | 1 | 0 | 0.000041 | ValueError: Tool 'calculator' missing arguments: expression |
| malformed_tool_arguments | adversarial | unbounded | 200 | no | 1 | 0 | 0.000019 | ValueError: Tool 'calculator' missing arguments: expression |
| model_returns_neither_action_nor_final | adversarial | bounded | 5 | no | 1 | 0 | 0.000016 | RuntimeError: Model returned neither action nor final answer |
| model_returns_neither_action_nor_final | adversarial | unbounded | 200 | no | 1 | 0 | 0.000013 | RuntimeError: Model returned neither action nor final answer |

## Scenario descriptions

| Scenario | Category | Description |
|----------|----------|--------------|
| quick_calc | success | One calculator call then finalize (2 steps). |
| kb_react | success | One knowledge_base lookup then finalize (2 steps). |
| kb_reflection | success | One knowledge_base lookup then finalize (2 steps). |
| kb_plan_execute | success | One knowledge_base lookup then finalize (2 steps). |
| immediate_answer | success | No tool call needed at all (1 step). |
| calc_then_kb | success | Two tool calls (calculator, knowledge_base) then finalize (3 steps). |
| kb_then_calc | success | Two tool calls (knowledge_base, calculator) then finalize (3 steps). |
| three_tool_chain | success | Three tool calls then finalize (4 steps) — under bounded budget. |
| boundary_fits_bounded_budget | success | Four tool calls then finalize on step 5 — exactly equal to max_steps=5. |
| exceeds_bounded_budget | success | Six tool calls then finalize on step 7 — a real, finite task that bounded mode (max_steps=5) cannot complete in time but unbounded mode (max_steps=200) completes normally. |
| runaway_calculator_only | runaway | Model always calls calculator, never emits final_answer. |
| runaway_knowledge_base_only | runaway | Model always calls knowledge_base, never emits final_answer. |
| runaway_alternating_tools | runaway | Model alternates calculator/knowledge_base forever, never finalizes. |
| malformed_tool_arguments | adversarial | Calculator called with no 'expression' argument on every attempt — Tool.invoke raises ValueError on step 1, independent of max_steps. |
| model_returns_neither_action_nor_final | adversarial | decide() returns neither action nor final_answer — agent.py raises RuntimeError on step 1, independent of max_steps. |

## Methodology notes

- **Deterministic stub, by design.** Every model in this benchmark is a hand-written Python class implementing the `ReasoningModel` protocol from `models.py`. None of them call an LLM API. This matches the repo's disclosed architecture — see README: "Deterministic model stub — `pytest` without API keys" and "Curriculum stub... not a production agent fleet." This benchmark measures the *loop's* mechanical behavior (does the step budget actually bound execution; does it fail safely), not model reasoning quality.
- **`steps_used`** counts real calls to `model.decide()` (tracked via a per-model call counter), i.e. real loop iterations attempted — including the final iteration that either finalizes or exhausts the budget.
- **`tool_calls`** counts real executions of a tool's handler body (tracked via a counting wrapper around each `Tool` in a fresh `ToolRegistry` per trial). A tool call that fails argument validation before the handler runs (`Tool.invoke`'s required-key check) correctly does NOT increment this counter — see the `malformed_tool_arguments` trial, which shows `tool_calls=0` because the handler body never executed.
- **"Unbounded" is a finite surrogate (`max_steps=200`), not literal infinity.** A truly unbounded runaway loop cannot be benchmarked in finite time. The real, exact numbers at the 200-step cap are reported above — they are not rounded up to "infinite" or otherwise estimated.
- **Adversarial scenarios are not "fixed" by bounding steps.** `malformed_tool_arguments` and `model_returns_neither_action_nor_final` both fail at step 1 in BOTH bounded and unbounded mode, with identical exceptions (`ValueError` / `RuntimeError` from `agent.py` and `tools.py`). The step budget protects specifically against non-terminating decision policies (the runaway scenarios); it does not, and was never meant to, catch malformed tool calls or invalid model decisions. That is a real, honest finding from this run, not a claimed feature.
- **Reproduce:** `python scripts/benchmark_bounded_loop.py` from the repo root regenerates this file with identical numbers (fully deterministic, no network, no keys).
