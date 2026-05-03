# Architecture Decision Record: ReAct Agent Pattern

## Context

Production AI teams often begin with a single prompt and gradually add retrieval, API calls, calculators, search, and business-system actions. Without an orchestration pattern, the assistant either guesses when it should use tools or loops through tool calls without a reliable stop condition. ReAct solves this by making the cycle explicit: reason, act, observe, and decide whether to continue.

## Decision

This repo implements ReAct as a bounded orchestration loop with four isolated responsibilities:

1. `ReasoningModel` decides the next thought, action, arguments, or final answer.
2. `ToolRegistry` owns available actions and validates tool existence.
3. `Tool` implementations own side effects, argument validation, and domain behavior.
4. `Trace` records every decision and observation for auditability.

The agent never imports a model SDK or embeds tool logic directly. That boundary is intentional: production systems need to swap model providers, enforce tool policies, add retries, and replay traces without rewriting the orchestration core.

## When To Use

Use ReAct when the task is interactive, tool-driven, and relatively shallow:

- Enterprise copilots that query APIs or knowledge bases.
- Q&A over internal systems.
- Assistants that need calculators, search, retrieval, or ticket lookup.
- API assistants that choose among a known set of actions.

Avoid ReAct as the top-level pattern when work requires deep decomposition, multiple specialist roles, or long-running background execution. In those cases, ReAct is better used inside a Plan and Execute worker or a specialized multi-agent role.

## Runtime Flow

```text
User request
  -> model decides thought/action
  -> tool executes action
  -> observation is appended to short-term state
  -> model decides continue or final answer
```

The loop terminates when the model emits a final answer or when `max_steps` is reached. The step budget is a production control for cost, latency, and hallucination-loop containment.

## State Model

The reference implementation keeps state in an in-memory list of observations. In production, split state into:

- Request state: user input, current observations, step count.
- Tool state: idempotency key, arguments, tool result, error details.
- Audit state: trace events, model metadata, policy decisions, token and cost accounting.
- Optional memory: retrieved facts or user preferences, never unfiltered chain-of-thought.

Persist traces to an append-only store. Persist business side effects through the tool layer with idempotency keys.

## Guardrails

- Tool allow-listing through `ToolRegistry`.
- Required argument validation at the tool boundary.
- Maximum step budget.
- Structured trace events for observability and incident review.
- Safe calculator sandbox in the sample tool.

Recommended production additions:

- JSON schema validation for model tool calls.
- Human approval gates for irreversible tools.
- Policy engine for user, tenant, and tool-level authorization.
- Circuit breakers per tool and per model provider.
- PII redaction before traces are exported.

## Failure Modes

- Tool hallucination: model asks for a tool that does not exist. Mitigation: registry validation and model output schema.
- Infinite reasoning loop: model repeatedly calls tools without finalizing. Mitigation: step budget and loop detectors.
- Stale observations: model over-trusts old tool outputs. Mitigation: timestamped observations and freshness policies.
- Cost runaway: unbounded tool/model calls. Mitigation: per-request budgets and admission control.

## Scaling Strategy

Start with an in-process agent for low-latency copilots. Move tools behind service interfaces as side effects grow. For high-volume systems, put each tool invocation behind a queue with idempotent handlers, distributed tracing, and result caching. ReAct itself should remain stateless between requests except for explicitly injected memory.

## Technology Choices

This repo uses only Python standard library code so the architecture is visible without framework noise. A production implementation can map the same boundaries to LangGraph nodes, OpenAI tool calling, Semantic Kernel planners, or a custom orchestration service.

## Success Metrics

- Tool-call precision and recall.
- First-pass grounded answer rate.
- Average tool calls per successful request.
- Step-budget exhaustion rate.
- Cost and latency per completed task.
- Human escalation rate for unsafe or ambiguous actions.

