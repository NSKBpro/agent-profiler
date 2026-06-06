# AGENTS.md

You are implementing a local-first coding-agent profiler.

Read this first:

- docs/copilot_agent_profiler_agent_contract.md

## Goal

Build a simple local CLI that can test/profile coding-agent runs.

The first version must support:

1. `agent-profiler init`
2. `agent-profiler start --case <id>`
3. `agent-profiler run <command>`
4. `agent-profiler finish`
5. `agent-profiler report --run latest`

## Hard rules

- Keep it simple.
- Do not build SaaS.
- Do not build dashboard.
- Do not add GitHub API integration yet.
- Do not add PR integration yet.
- Do not add LLM/AI analysis yet.
- Core analysis must be local and deterministic.
- Do not commit.
- Do not push.
- Add tests for implemented behavior.
- Keep code clean and typed.

## MVP features

Implement:

- Python package skeleton
- CLI entry point
- local `.agent-profiler/` folder
- config file generation
- run metadata JSON
- git snapshot before/after run
- command execution capture
- basic test case YAML loading
- markdown report generation

Add only these first rules:

1. Missing required report
2. Forbidden file changed
3. Repeated command failure
4. Large command output warning

## Validation

Run when possible:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .