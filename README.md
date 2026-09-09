# Agent OS V1

A provider-neutral control-plane foundation for a persistent AI agent operating system.

## Purpose

Agent OS V1 provides the execution, cognition, memory, skills, tools, observability,
recovery, configuration, and evaluation boundaries needed to build a persistent
AI agent system without coupling the core runtime to a specific model provider.

V1 is deliberately a foundation. It does **not** claim to be AGI, autonomous general
intelligence, or a complete production agent platform.

## Cognitive Lifecycle

Each task follows an explicit lifecycle:

1. **INTAKE** — normalize the task and constraints.
2. **MEMORY_RETRIEVAL** — retrieve relevant persistent context.
3. **PLANNING** — construct an explicit plan.
4. **EXECUTION** — perform bounded agent and tool actions.
5. **VERIFICATION** — compare results against expected outcomes.
6. **FINALIZATION** — prepare the run result.
7. **MEMORY_CONSOLIDATION** — persist justified durable information.
8. **COMPLETE** — finish the successful run.

Failures transition the run to `FAILED` and are recorded for observability.

## Implemented V1 Components

- **Core orchestration** — explicit task state and lifecycle execution.
- **Cognition** — planning, prediction, verification, and reflection primitives.
- **Persistent memory** — SQLite-backed storage, retrieval, and provenance.
- **Skills** — versioned skill definitions, loading, selection, and procedure execution.
- **Tools** — explicit registration, permission enforcement, bounded execution, retries,
  and audit records.
- **Agents** — provider-backed execution with structured tool-call results.
- **Providers** — provider-neutral interface with a deterministic mock provider.
- **Recovery** — bounded retry policies and runtime failure classification.
- **Observability** — lifecycle events, durable run records, logging, and tracing primitives.
- **Evaluation** — deterministic datasets, keyword-based evaluation, metrics, and runners.
- **Configuration** — validated runtime configuration with configurable memory and provider
  settings.

## Trust Boundaries

The runtime follows several explicit boundaries:

- External content is treated as untrusted input.
- Secrets must not be exposed through prompts or logs.
- Tools must be registered before execution.
- Tool permissions are separate from skill procedures.
- Important outputs are verified before finalization.
- Unexpected agent execution failures are contained and persisted as failed runs.

## Repository Layout

```text
src/agent_os/
├── agents/          Agent interfaces and management
├── cognition/       Planning, prediction, verification, reflection
├── config/          Runtime configuration
├── core/            Orchestration, state, events, recovery, failures
├── evaluation/      Evaluation metrics and runners
├── memory/          Persistent memory and provenance
├── observability/   Logging, tracing, durable run records
├── providers/       Provider abstraction and mock provider
├── skill_runtime/   Skill loading, selection, and execution
└── tools/           Tool registry, permissions, execution, audit

evals/               Evaluation datasets
memory/              SQLite schema
skills/              Versioned skill definitions
tests/               V1 test suite

## Development

Requirements:

- Python 3.11+
- `pytest` for development/testing

Install the project with development dependencies:

    python -m pip install -e '.[dev]'

Run the complete test suite:

    pytest -q

## Design Principles

Agent OS V1 follows:

**capability → implementation → evaluation → evidence**

A capability is considered part of the foundation only when it has an implementation boundary and executable tests supporting its behavior.

## Future Extensions

The architecture leaves room for:

- LLM provider adapters
- vector retrieval
- knowledge-graph reasoning
- MCP/tool integrations
- multi-agent systems
- automated evaluation and skill improvement
- richer observability and dashboards

These are future extensions, not claims about the current V1 implementation.
