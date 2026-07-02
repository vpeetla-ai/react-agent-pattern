# ReAct Agent Pattern


<!-- vpeetla-tech-stack:start -->
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square)]() [![LangGraph](https://img.shields.io/badge/LangGraph-9333EA?style=flat-square)]() [![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square)]() [![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square)]()
<!-- vpeetla-tech-stack:end -->
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://react-agent-pattern.vercel.app)
[![Part of Production Agent Patterns](https://img.shields.io/badge/series-Production%20Agent%20Patterns-purple)](https://github.com/vpeetla-ai/react-agent-pattern)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Production reference for ReAct loops** — explicit thought → action → observation with bounded iterations. Used in **VAP Deep Research**.

[▶ Live demo](https://react-agent-pattern.vercel.app) · [Architecture](docs/ARCHITECTURE.md) · [Portfolio](https://venkat-ai.com/work) · [Pattern series](https://github.com/vpeetla-ai/ai-content-factory/blob/main/docs/agent-patterns/ROADMAP.md)

## What this is

Part **1 of 5** in Production Agent Patterns — tool-using assistants, retrieval workflows, and enterprise Q&A with inspectable traces.

## How we solve it

| Problem | Approach |
|---------|----------|
| Monolithic LLM calls | Explicit ReAct loop with stop conditions |
| Runaway tool loops | Bounded iterations + schema-light validation |
| Untestable agents | Deterministic model stub — `pytest` without API keys |

## Case study & tradeoffs

No standalone case study — see [venkat-ai.com/work](https://venkat-ai.com/work) and [VAP case study](https://github.com/vpeetla-ai/ai-architecture-portfolio/blob/main/case-studies/venkat-ai-platform.md). Tradeoffs in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Status

| Component | Status | Notes |
|-----------|--------|-------|
| Pattern demo + trace UI | ✅ | Live Vercel demo |
| Core agent loop | ✅ | Reference implementation |
| LangGraph production graph | 🟡 | Teaching scope — compose into VAP for fleet use |
| MCP tool bridge | ❌ | See LoopForge / VAP MCP docs |
| AegisAI gateway | ❌ | No side effects in pattern demo |
| Pytest regression | ✅ | `pytest -q` in repo |

## Agent skills (Cursor + Codex)

Org skills: [vpeetla-ai-skills](https://github.com/vpeetla-ai/vpeetla-ai-skills).

```bash
git clone https://github.com/vpeetla-ai/vpeetla-ai-skills.git
./vpeetla-ai-skills/scripts/install.sh --cursor --codex --project .
```

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m react_agent_pattern
pytest
```

The default demo uses a deterministic model stub so the architecture can be tested **without external API keys**.

```bash
cp .env.example .env
```

For LLM keys, database config, and production adapters, see [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md).

## Repo layout

```text
src/react_agent_pattern/
  __main__.py       # CLI demo
  agent.py          # ReAct orchestration loop
  models.py         # Model protocol + deterministic demo model
  tools.py          # Tool interface and sample tools
  tracing.py        # Structured trace events
docs/
  ARCHITECTURE.md   # Architect-level design decision record
tests/
  test_react_agent.py
```

## Production mapping

Replace `ScriptedReasoningModel` with an LLM gateway that supports tool-call structured output. Keep boundaries intact: the agent should not know vendor SDK details, and tools should remain independently testable.

## Related

- **Next in series:** [Reflection Agent Pattern](https://github.com/vpeetla-ai/reflection-agent-pattern)
- **Full pipeline:** [AI Content Factory](https://github.com/vpeetla-ai/ai-content-factory) — multi-agent content orchestration with HITL

If this helped you, ⭐ the repo — and star the [series](https://github.com/vpeetla-ai) to follow new patterns.
