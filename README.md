# ReAct Agent Pattern

Production-grade reference implementation of the ReAct (Reason + Act) pattern for tool-using assistants, retrieval workflows, API copilots, and enterprise Q&A.

## What This Repo Demonstrates

- Explicit thought/action/observation loop with bounded iterations.
- Tool contracts with schema-light validation and deterministic tests.
- Stop conditions that prevent hallucination loops and runaway cost.
- Separation between model reasoning, tool execution, orchestration, and audit traces.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m react_agent_pattern
pytest
```

The default demo uses a deterministic model stub so the architecture can be tested without external API keys.

For local setup, environment variables, LLM API keys, database configuration, and production adapter guidance, see [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md).

Create your local secret file from:

```bash
cp .env.example .env
```

## Repo Layout

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

## Production Mapping

Replace `ScriptedReasoningModel` with an LLM gateway that supports tool-call structured output. Keep the rest of the boundaries intact: the agent should not know vendor SDK details, and tools should remain independently testable.
