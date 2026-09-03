"""Real merge gate: runs the shared `react_agent_pattern.bounded_loop_v1`
suite from vpeetla-ai/golden-eval-registry against this repo's real
`ReActAgent` loop (via scripts/benchmark_bounded_loop.py's `run_trial`),
scored through the registry's own `golden_eval_registry.runner.score_suite`.

Mirrors the convention used by
vpeetla-ai/aegisloop-agentops-workbench/services/api/tests/test_golden_eval_gate.py:
skip locally when the sibling registry repo isn't checked out; CI always
checks it out first (see .github/workflows/ci.yml) and points
GOLDEN_EVAL_REGISTRY_PATH at it.

The suite uses the registry's existing `router_invariant` kind/scorer
(exact-match `equals` checks) rather than a new scorer kind — see the
suite's manifest.json `description` for why. `actual` per case is built by
actually running that case's scenario through `ReActAgent` in both bounded
(max_steps=5) and unbounded-surrogate (max_steps=200) mode — the same
deterministic model stubs the benchmark script and docs/receipts/benchmark.md
are generated from, not hand-typed numbers.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from benchmark_bounded_loop import (  # noqa: E402
    BOUNDED_MAX_STEPS,
    SCENARIOS,
    UNBOUNDED_MAX_STEPS,
    run_trial,
)

try:
    from golden_eval_registry.runner import score_suite
    from golden_eval_registry.schema import parse_manifest
    from golden_eval_registry.validate import load_jsonl

    GOLDEN_EVAL_REGISTRY_AVAILABLE = True
except ImportError:
    GOLDEN_EVAL_REGISTRY_AVAILABLE = False

REGISTRY_PATH = Path(os.getenv("GOLDEN_EVAL_REGISTRY_PATH", "../golden-eval-registry")).resolve()
SUITE_DIR = REGISTRY_PATH / "suites" / "react_agent_bounded_loop_v1"

SCENARIOS_BY_ID = {s.id: s for s in SCENARIOS}


def _actual_for_case(case: dict) -> dict:
    scenario_id = case["input"]["scenario_id"]
    scenario = SCENARIOS_BY_ID[scenario_id]
    bounded = run_trial(scenario, BOUNDED_MAX_STEPS, "bounded")
    unbounded = run_trial(scenario, UNBOUNDED_MAX_STEPS, "unbounded")
    return {
        "bounded_succeeded": bounded.succeeded,
        "bounded_steps_used": bounded.steps_used,
        "unbounded_succeeded": unbounded.succeeded,
        "unbounded_steps_used": unbounded.steps_used,
    }


@unittest.skipUnless(
    GOLDEN_EVAL_REGISTRY_AVAILABLE and SUITE_DIR.exists(),
    "golden-eval-registry not available — set GOLDEN_EVAL_REGISTRY_PATH or run in CI",
)
class GoldenEvalGateTests(unittest.TestCase):
    def test_react_agent_bounded_loop_v1_suite_passes(self) -> None:
        manifest = parse_manifest(SUITE_DIR / "manifest.json")
        cases = load_jsonl(manifest.cases_path)
        self.assertGreaterEqual(len(cases), 10)

        actual_by_id = {str(case["id"]): _actual_for_case(case) for case in cases}

        result = score_suite(manifest, cases, actual_by_id)
        failures = "\n".join(f"{failure.case_id}: {failure.detail}" for failure in result.failures)
        self.assertTrue(result.passed, f"golden eval regressions:\n{failures}")


if __name__ == "__main__":
    unittest.main()
