# MVP Acceptance Checklist

The MVP is accepted only when this full scenario works locally.

---

## Required project files

The project must contain:

```text
pyproject.toml
README.md
agent_profiler/
tests/
AGENTS.md
docs/
```

---

## Required commands

The CLI must support:

```bash
agent-profiler init
agent-profiler start --case sample-case
agent-profiler run <command>
agent-profiler finish
agent-profiler report --run latest
```

---

## Required local folders

After running:

```bash
agent-profiler init
```

this must exist:

```text
.agent-profiler/
  config.yml
  cases/
  runs/
  reports/
  command-logs/
```

---

## Required sample case

The MVP must create or support this file:

```text
.agent-profiler/cases/sample-case.yml
```

Example:

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

---

## Required end-to-end test

This must work:

```bash
agent-profiler init
agent-profiler start --case sample-case
agent-profiler run python -c "print('hello')"
agent-profiler finish
agent-profiler report --run latest
```

---

## Required report output

After report generation, this must exist:

```text
.agent-profiler/reports/<run-id>.md
```

The report must include:

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

---

## Required findings

The MVP must support these findings:

### 1. Missing required report

Detect when a test case requires a report file and it was not created.

### 2. Forbidden file changed

Detect when changed files match forbidden paths.

### 3. Repeated command failure

Detect when the same command failure signature appears more than once.

### 4. Large command output

Warn when command output is too large.

---

## Required scoring

The report must include a score out of 100.

Default scoring:

```text
Correctness: 40
Instruction compliance: 20
Scope control: 15
Validation quality: 10
Efficiency: 10
Report quality: 5
```

The scoring can be simple in MVP, but it must be visible and explainable.

---

## Required tests

At minimum, tests must cover:

* init creates folder structure
* sample case can be loaded
* command run is captured
* missing report rule works
* forbidden path rule works
* repeated failure rule works
* Markdown report is generated

---

## Required validation

Codex should run when possible:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

If Ruff is not configured yet, Codex should add minimal Ruff configuration.

---

## Required implementation report

At the end, Codex must update:

```text
.agent-profiler/reports/implementation-report.md
```

It must include:

```markdown
# Implementation Report

## What was implemented

## Files changed

## Commands run

## Validation result

## Known limitations

## Next recommended step
```

---

## MVP is not accepted if

* CLI does not run
* no Markdown report is generated
* no tests exist
* core analysis requires an LLM
* GitHub API is required
* SaaS/dashboard code was added
* project is overcomplicated with unnecessary infrastructure

```
```
