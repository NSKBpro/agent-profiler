# Copilot Agent Profiler - Implementation Phases

## Purpose

This document defines the implementation phases for the local-first coding-agent profiler.

The project must be implemented in small, controlled phases. Do not jump to SaaS, dashboards, GitHub API integration, or LLM analysis before the local MVP works.

---

## Phase 0 - Project Setup

### Goal

Create the basic Python project structure.

### Must implement

* `pyproject.toml`
* Python package folder
* CLI entry point
* test folder
* basic README
* `.agent-profiler/reports/implementation-report.md`

### Expected structure

```text
agent_profiler/
  __init__.py
  cli.py

tests/
  test_cli.py

pyproject.toml
README.md
```

### Done when

* project installs locally
* CLI can be called
* tests can run

---

## Phase 1 - Init Command

### Goal

Implement:

```bash
agent-profiler init
```

### Must implement

The command creates:

```text
.agent-profiler/
  config.yml
  cases/
  runs/
  reports/
  command-logs/
```

### Done when

Running:

```bash
agent-profiler init
```

creates the folder structure and default config.

---

## Phase 2 - Test Case Loading

### Goal

Support YAML test cases.

### Must implement

Load files from:

```text
.agent-profiler/cases/
```

Example case:

```yaml
id: sample-case
title: Sample case
agent: unknown

task_prompt: >
  Run a simple command and generate a report.

expected:
  forbidden_paths:
    - .env
    - "**/*.secret"

validation:
  required_reports: []
  required_commands: []
```

### Done when

The tool can load a case by ID:

```bash
agent-profiler start --case sample-case
```

---

## Phase 3 - Start Command

### Goal

Implement:

```bash
agent-profiler start --case <id>
```

### Must implement

* verify git repository if available
* capture baseline snapshot
* store run metadata JSON
* store current branch
* store current commit hash
* store git status
* store case ID
* print task prompt for the user

### Done when

A run JSON is created under:

```text
.agent-profiler/runs/
```

---

## Phase 4 - Command Wrapper

### Goal

Implement:

```bash
agent-profiler run <command>
```

### Must implement

Capture:

* command
* start time
* end time
* duration
* exit code
* stdout
* stderr
* output size
* failure signature for failed commands

### Done when

This works:

```bash
agent-profiler run python -c "print('hello')"
```

and command metadata is stored in the active run.

---

## Phase 5 - Finish Command

### Goal

Implement:

```bash
agent-profiler finish
```

### Must implement

* capture final git status
* capture git diff
* detect changed files
* count changed files
* count added/removed lines where possible
* store final snapshot
* mark run as finished

### Done when

After changing a file, `finish` records the changed file list.

---

## Phase 6 - Basic Rules

### Goal

Implement deterministic local analysis rules.

### Required rules

1. Missing required report
2. Forbidden file changed
3. Repeated command failure
4. Large command output warning

### Done when

Each rule produces a finding with:

* ID
* severity
* confidence
* title
* evidence
* recommendation

---

## Phase 7 - Markdown Report

### Goal

Implement:

```bash
agent-profiler report --run latest
```

### Must generate

```text
.agent-profiler/reports/<run-id>.md
```

### Report sections

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

### Done when

A readable Markdown report is generated from the latest run.

---

## Phase 8 - Scoring

### Goal

Add simple scoring.

### Score categories

```text
Correctness: 40
Instruction compliance: 20
Scope control: 15
Validation quality: 10
Efficiency: 10
Report quality: 5
```

### Done when

Report includes a score out of 100.

---

## Phase 9 - Better Local Rules

Only after MVP works, add:

* formatting-heavy diff
* mechanical repeated edit
* broad file spread
* full test suite overuse
* lock file changed unexpectedly
* missing tests
* generated file changed manually
* low reviewability

---

## Phase 10 - Agent Comparison

Only after multiple runs exist, add:

```bash
agent-profiler compare --last 10
```

### Must compare

* average score
* repeated findings
* pass/fail count
* most common bottlenecks

---

## Phase 11 - GitHub Integration

Do not implement before local MVP is stable.

Later features:

* scan PRs
* attach reports to PRs
* import Copilot usage metrics
* analyze PR lifecycle
* map agent runs to merged/rejected PRs

---

## Phase 12 - Other Agent Adapters

Do not implement before local MVP is stable.

Later adapters:

* Codex
* Claude Code
* Cursor
* custom LangGraph agents

---

## Implementation Rule

Never start a later phase until the previous phase works.

The first real target is only:

```text
agent-profiler init
agent-profiler start --case sample-case
agent-profiler run python -c "print('hello')"
agent-profiler finish
agent-profiler report --run latest
```
