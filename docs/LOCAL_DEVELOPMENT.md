# Local Development Guide

## Current Runtime Behavior

This repo runs locally without any LLM API key by default. The demo uses `ScriptedReasoningModel`, a deterministic model stub that exercises the ReAct orchestration loop:

```text
thought -> action -> tool observation -> final answer
```

This is intentional. You should validate orchestration, state transitions, tool contracts, and traces before introducing nondeterministic LLM behavior.

## 1. Create a Virtual Environment

```bash
cd /Users/lakshmipraveenabodempudi/react-agent-pattern
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. Run the Local Stub Demo

```bash
python -m react_agent_pattern
```

Expected behavior:

- The agent receives a calculation request.
- The model stub selects the calculator tool.
- The calculator returns an observation.
- The agent finalizes a grounded answer.
- A structured trace is printed.

You can also run it without creating a virtual environment:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m react_agent_pattern
```

## 3. Run Tests

```bash
pytest
```

If `pytest` is not installed globally, use the virtual environment setup above.

## 4. Environment Variables

Create a local `.env` file from the template:

```bash
cp .env.example .env
```

The `.env` file is ignored by git. Add real secrets there only on your machine or through your deployment secret manager.

Key variables:

| Variable | Purpose |
| --- | --- |
| `AGENT_RUNTIME_MODE` | `local_stub` for deterministic local mode, `llm` for real provider mode |
| `OPENAI_API_KEY` | OpenAI API key when using an OpenAI model gateway |
| `ANTHROPIC_API_KEY` | Anthropic API key if you add an Anthropic gateway |
| `GOOGLE_API_KEY` | Google model API key if you add a Gemini gateway |
| `DATABASE_URL` | Relational database for persisted traces or tool data |
| `REDIS_URL` | Cache, rate-limit, or short-lived workflow state |
| `VECTOR_DATABASE_URL` | Retrieval/vector backend |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint |
| `MAX_AGENT_STEPS` | ReAct loop step budget |
| `MAX_REQUEST_COST_USD` | Per-request cost budget |

## 5. Where To Add Real LLM Support

The LLM integration point is:

```text
src/react_agent_pattern/models.py
```

Add a new class that implements `ReasoningModel`:

```python
class OpenAIReasoningModel:
    def decide(self, user_input, tool_descriptions, observations):
        ...
```

The new model adapter should:

- Read provider settings from environment variables.
- Return a `ModelDecision`.
- Validate structured model output.
- Enforce timeout and retry limits.
- Never execute tools directly.

Keep tool execution inside:

```text
src/react_agent_pattern/tools.py
```

## 6. Where To Add Database Support

The current trace is in memory:

```text
src/react_agent_pattern/tracing.py
```

For production, add a trace sink such as:

```python
class DatabaseTraceSink:
    def write(self, trace_event):
        ...
```

Recommended tables:

- `agent_requests`
- `agent_trace_events`
- `tool_invocations`
- `policy_decisions`
- `cost_records`

## 7. Production Readiness Checks

Before using this pattern with real tools:

- Tool calls use schemas.
- Unknown tools fail closed.
- Side-effectful tools require authorization.
- `MAX_AGENT_STEPS` is enforced.
- Traces are persisted.
- PII is redacted before export.
- Cost and latency are measured per request.

