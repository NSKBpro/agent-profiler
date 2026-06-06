# Agent Profiler

`agent-profiler` is a local-first CLI tool for profiling coding-agent runs.

It is designed for testing and reviewing GitHub Copilot/custom agent workflows first, with possible future support for Codex, Claude Code, Cursor, and other coding agents.

The core idea is simple: treat the coding agent as a black box, then analyze what happened locally.

No SaaS.
No GitHub API required.
No LLM analysis required.
No cloud dependency.

---

## What It Does

`agent-profiler` captures and analyzes a local coding-agent run using:

* git snapshots
* git diffs
* changed files
* wrapped command execution
* command logs
* test/validation commands
* required reports
* deterministic rule findings
* Markdown reports
* simple scoring

The goal is to answer questions like:

* Did the agent follow the requested scope?
* Did it touch forbidden files?
* Did it run useful validation?
* Did it repeat failing commands?
* Did it produce required reports?
* Did it make the change too broad or hard to review?
* Did it create obvious local workflow bottlenecks?

---

## Current Status

Current implementation includes:

* MVP local CLI
* deterministic rule engine
* Markdown run reports
* scoring
* Phase 9 local profiling rules
* test coverage
* local repository hygiene for generated run data

This is still intentionally local and simple. It is not a SaaS product and does not require GitHub integration.

---

## Installation

From the repository root:

```bash
pip install -e .
```

For development dependencies:

```bash
pip install -e .[dev]
```

---

## Quick Start

From the repository root, initialize the local profiler files:

```bash
agent-profiler init
```

Start a run using the included sample case. The command prints the task prompt
for the agent or manual workflow being profiled:

```bash
agent-profiler start --case sample-case
```

Run validation or diagnostic commands through the profiler so their output and
exit codes are captured:

```bash
agent-profiler run python -c "print('hello')"
```

Finish the run to capture the final git state and apply deterministic rules:

```bash
agent-profiler finish
```

Generate the latest run's Markdown report:

```bash
agent-profiler report --run latest
```

Reports are generated under:

```text
.agent-profiler/reports/
```

---

## Basic Workflow

A normal local profiling session looks like this:

```bash
agent-profiler init
agent-profiler start --case sample-case
agent-profiler run <command>
agent-profiler finish
agent-profiler report --run latest
```

The coding agent itself is not controlled by `agent-profiler`.

Instead, `agent-profiler` wraps selected commands and inspects the repository before and after the agent run.

---

## Project Structure

```text
agent-profiler/
├── src/
│   └── agent_profiler/
├── tests/
├── docs/
├── AGENTS.md
├── pyproject.toml
├── README.md
└── .agent-profiler/
    ├── config.yml
    ├── cases/
    └── reports/
```

Generated local runtime data is ignored by git:

```text
.agent-profiler/runs/
.agent-profiler/command-logs/
.agent-profiler/snapshots/
.agent-profiler/reports/*.md
```

The implementation report is intentionally kept:

```text
.agent-profiler/reports/implementation-report.md
```

---

## Test Cases

Profiler cases live under:

```text
.agent-profiler/cases/
```

Example case:

```yaml
id: sample-case
title: Sample case
agent: unknown

task_prompt: >
  Run a simple command and generate a local profiler report.

expected:
  forbidden_paths:
    - .env
    - "**/*.secret"

validation:
  required_reports: []
  required_commands: []
```

A case defines what the agent is supposed to do and what local expectations should be checked.

---

## Rules

The profiler currently supports MVP rules and additional deterministic local rules.

### MVP Rules

* missing required report
* forbidden file changed
* repeated command failure
* large command output warning

### Additional Local Rules

* formatting-heavy diff
* mechanical repeated edit
* broad file spread
* full test suite overuse
* lock file changed unexpectedly
* missing tests
* generated file changed manually
* low reviewability

Each finding includes:

* ID
* severity
* confidence
* title
* evidence
* recommendation

---

## Reports

A generated report includes:

```markdown
# Agent Run Report

## Summary
## Run Metadata
## Task and Agent
## Changed Files
## Commands Run
## Findings
## Recommendations
## Final Verdict
```

Reports also include scoring, grouped findings, and optional usage/cost details when a local usage file is attached.

The score is intentionally simple and explainable.

Default scoring categories:

```text
Correctness: 40
Instruction compliance: 20
Scope control: 15
Validation quality: 10
Efficiency: 10
Report quality: 5
```

---

## Validation

Run tests:

```bash
python -m pytest
```

Run Ruff:

```bash
python -m ruff check .
python -m ruff format --check .
```

Expected current validation:

```text
python -m pytest                 passing
python -m ruff check .           passing
python -m ruff format --check .  passing
```

---

## What This Project Is Not

`agent-profiler` is currently not:

* a SaaS platform
* a dashboard
* a GitHub PR bot
* a GitHub Copilot usage importer
* an LLM-based code reviewer
* a replacement for tests
* a replacement for human review

It is a local deterministic profiler for coding-agent runs.

---

## Planned Next Steps

Near-term possible next step:

* compare multiple local agent runs

Future ideas:

* GitHub integration
* PR report attachment
* provider usage import
* Codex adapter
* Claude Code adapter
* Cursor adapter
* optional LLM-assisted analysis

These should only be added after the local deterministic workflow proves useful.

---

## Design Principle

Keep the profiler boring.

The first version should be:

* local
* deterministic
* inspectable
* easy to run
* easy to delete
* useful without cloud services
* useful without LLM analysis

The tool should help developers understand whether coding agents are actually helping, wasting time, breaking scope, or creating review debt.
