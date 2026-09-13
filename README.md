# Agent OS V2

A provider-neutral control-plane foundation for a persistent AI agent operating system.

## Purpose

Agent OS V2 provides an integrated, provider-neutral control plane for persistent AI
agents, combining explicit orchestration, persistent memory, versioned skills, bounded
tool execution, MCP integration, multi-agent coordination, governance, evaluation,
recovery, observability, and production-oriented resource lifecycle management.

V2 is an engineering platform, not a claim of AGI or autonomous general intelligence.
The system provides explicit boundaries, verification, governance, and evaluation rather
than assuming that model capability alone guarantees reliable autonomy.

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

## Implemented V2 Components

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
tests/               V2 test suite

## Development

Requirements:

- Python 3.11+
- `pytest` for development/testing

Install the project with development dependencies:

    python -m pip install -e '.[dev]'

Run the complete test suite:

    pytest -q

## Design Principles

Agent OS V2 follows:

**capability → implementation → evaluation → evidence → controlled execution**

A capability is considered part of the foundation only when it has an implementation boundary and executable tests supporting its behavior.

## V2 Release-Candidate Scope

The V2 release candidate includes:

- persistent memory and provenance-aware retrieval
- explicit cognitive orchestration and lifecycle state
- versioned skills and iterative skill improvement
- scoped agent instructions and workspace boundaries
- explicit tool registration and permission enforcement
- MCP protocol integration and stdio transport
- MCP capability and input-schema enforcement
- multi-agent coordination and swarm governance
- human-judgment and approval boundaries
- evaluation, verification, recovery, and observability
- production-oriented resource lifecycle hardening

V2 remains intentionally provider-neutral. Model quality, external services, and deployment
infrastructure can vary independently of the control-plane architecture.
