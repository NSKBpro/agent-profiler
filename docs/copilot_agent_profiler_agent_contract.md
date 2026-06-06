# Copilot Agent Profiler — Agent Execution Contract

## 1. Purpose

This document defines the expected behavior for an AI coding agent that will help design and implement a local-first **Copilot Agent Profiler**.

The goal is not to build another generic AI dashboard. The goal is to build a practical developer tool that tests, profiles, and improves coding agents, starting with GitHub Copilot custom agents and later supporting Claude Code, Codex, Cursor, and custom local agents.

The profiler must answer these questions:

- Is this agent actually useful?
- Did the agent complete the task correctly?
- Did the agent follow instructions?
- Did the agent stay in scope?
- Did the agent waste effort on deterministic work?
- Which workflow step caused the bottleneck?
- What should be improved in the agent instructions, workflow, or validation process?
- What could be replaced by scripts, linters, formatters, static analyzers, or deterministic automation?

The first version must work locally, without requiring a SaaS backend and without requiring an LLM call for the core analysis.

---

## 2. Product Definition

### Working name

`copilot-agent-profiler`

Alternative names:

- `agenttest`
- `agent-profiler`
- `code-agent-profiler`
- `coding-agent-testkit`

### Product category

Local-first testing and profiling framework for coding agents.

### Primary target

GitHub Copilot custom agents and GitHub Copilot coding workflows.

### Later targets

- Claude Code
- OpenAI Codex
- Cursor agents
- Custom LangGraph coding agents
- Local SLM-based coding agents

### One-sentence pitch

A local-first profiler that tests coding agents, captures their work, detects bottlenecks and waste, and generates actionable reports for improving agent instructions, workflow quality, and token efficiency.

---

## 3. Core Principle

The profiler must treat the agent as a black box.

It must not depend on hidden model internals, hidden prompts, private Copilot context, or exact token counts that may not be available.

The profiler should analyze observable evidence:

- repository state before and after the run
- git diff
- changed files
- command execution logs
- validation results
- agent report artifacts
- instruction files
- timestamps
- repeated failures
- file scope
- output size
- test behavior
- deterministic automation opportunities

Exact token usage is optional and should only be included when reliable provider data is available.

---

## 4. Non-Goals

The first version must not try to do the following:

- Build a multi-tenant SaaS platform.
- Require GitHub organization admin permissions.
- Depend on exact Copilot internal token data.
- Depend on a cloud LLM for core analysis.
- Automatically control every Copilot agent execution.
- Replace human code review.
- Claim perfect cost calculation.
- Claim perfect semantic understanding of the task.
- Build a generic LLM observability platform.

The MVP must stay focused on local testing, local profiling, deterministic analysis, and useful reports.

---

## 5. Operating Modes

The tool must support three modes.

### 5.1 Static inspection mode

This mode runs before any agent execution.

Command example:

```bash
agent-profiler inspect
```

It analyzes:

- custom agent files
- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.github/instructions/**/*.instructions.md`
- expected report paths
- validation command definitions
- forbidden actions
- stop conditions
- output requirements
- scope rules

It produces a readiness report.

Purpose:

- Detect weak agent definitions before running the agent.
- Recommend missing instructions.
- Warn about agents that are too broad, unsafe, or hard to evaluate.

### 5.2 Single-run profiling mode

This mode profiles one agent run.

Command example:

```bash
agent-profiler start --case enumeration-fix
# user runs Copilot/custom agent manually
agent-profiler finish
agent-profiler report
```

It analyzes:

- what changed
- what commands ran
- whether validation passed
- whether reports were created
- whether the agent stayed in scope
- whether the agent looped
- whether deterministic tools should have been used instead

Purpose:

- Produce a full report for one agent run.

### 5.3 Regression suite mode

This mode compares many agent runs.

Command example:

```bash
agent-profiler suite run
agent-profiler compare --agent grid-ai-implementer --last 30d
```

It analyzes trends:

- pass rate
- average score
- scope violations
- repeated failures
- report completeness
- validation quality
- diff size
- deterministic automation opportunities
- improvement/regression after instruction changes

Purpose:

- Test whether new agent instructions improved or degraded behavior.

---

## 6. Local-First Design

The default version must run locally.

Default storage:

```text
.agent-profiler/
  config.yml
  cases/
  runs/
  reports/
  snapshots/
```

Recommended local storage:

- JSON files for run metadata
- Markdown reports for humans
- Optional HTML reports
- Optional SQLite later for querying multiple runs

The tool must not require internet access for the core report.

---

## 7. Core Workflow

### 7.1 Start

When the user starts a run, the profiler must:

1. Verify repository exists.
2. Verify git is available.
3. Check current git state.
4. Warn if the workspace is dirty.
5. Store baseline snapshot:
   - branch
   - commit hash
   - git status
   - file hashes for tracked files
   - existing report files
   - instruction file hashes
6. Load test case definition if provided.
7. Print the exact task prompt that the user should give to the agent.

Command:

```bash
agent-profiler start --case enumeration-fix
```

### 7.2 During Run

The user may run the agent manually.

The profiler should support optional command wrapping:

```bash
agent-profiler run pytest tests/unit/chunking
agent-profiler run ruff check .
```

When wrapping a command, the profiler must record:

- command
- working directory
- start time
- end time
- duration
- exit code
- stdout size
- stderr size
- output file path
- failure signature if command failed

### 7.3 Finish

When finishing a run, the profiler must collect:

- git status
- git diff
- changed files
- added/removed line counts
- changed folders
- report artifacts
- command logs
- validation results
- test result summaries
- repeated failure signatures
- forbidden file changes
- missing expected files
- missing reports

Command:

```bash
agent-profiler finish
```

### 7.4 Report

The profiler must generate:

```text
.agent-profiler/reports/<run-id>.md
.agent-profiler/reports/<run-id>.html
```

The Markdown report is mandatory.

The HTML report is optional for MVP but recommended.

---

## 8. Test Case Definition

Test cases should be YAML files.

Example:

```yaml
id: enumeration-fix
title: Fix enumeration chunking
agent: grid-ai-implementer

task_prompt: >
  Fix enumeration chunking so numbered list items that belong to the same
  section are not split into separate chunks. Keep the change small and add
  focused tests. Follow the repository instructions and create the required
  report artifact.

setup:
  commands:
    - python tests/fixtures/apply_enumeration_bug.py

expected:
  changed_paths_allowlist:
    - core/chunking/**
    - tests/**/chunking/**
    - .copilot/reports/agents/**

  forbidden_paths:
    - pyproject.toml
    - poetry.lock
    - docs/**
    - scripts/deployment/**
    - .env
    - "**/*.secret"

validation:
  required_commands:
    - ruff check .
    - pytest tests/unit/chunking

  required_reports:
    - .copilot/reports/agents/grid-ai-implementer-report.md

scoring:
  max_changed_files: 6
  max_failed_test_retries: 2
  require_tests_added: true
  require_report: true
  require_no_commits: true
```

The profiler must validate actual run evidence against this case definition.

---

## 9. Agent Readiness Checks

The static inspection mode must check agent and instruction files for the following.

### 9.1 Required sections

For custom coding agents, prefer these sections:

- Role
- Scope
- Allowed actions
- Forbidden actions
- Required workflow
- Required validation
- Stop conditions
- Required report artifact
- Output format
- Handoff rules, if applicable

### 9.2 Required constraints

The agent instructions should define:

- Do not commit unless explicitly requested.
- Do not push unless explicitly requested.
- Do not modify unrelated files.
- Do not edit secrets or environment files.
- Do not silently change dependency lock files.
- Run configured validation commands.
- Create or update the required Markdown report.
- Stop after repeated identical failures.
- Ask for human input when blocked.
- List files inspected and changed.
- List commands run and their result.
- State assumptions and limitations.

### 9.3 Weaknesses to detect

The profiler must warn when:

- agent role is too broad
- no validation command is specified
- no stop condition is specified
- no report artifact is required
- reviewer agent can edit files
- implementer agent has no scope restrictions
- dangerous tools are allowed without approval
- instructions are very long and duplicated
- output format is vague
- no allowed/forbidden paths are defined
- no deterministic pre-checks are defined

---

## 10. Evidence Collection

Each run must store structured evidence.

Suggested schema:

```json
{
  "run_id": "2026-06-06T14-20-00_enumeration-fix",
  "case_id": "enumeration-fix",
  "agent": "grid-ai-implementer",
  "repo_path": "C:/dev/project",
  "branch_before": "feature/test",
  "commit_before": "abc123",
  "commit_after": "def456",
  "started_at": "2026-06-06T14:20:00",
  "finished_at": "2026-06-06T14:45:00",
  "changed_files": [],
  "commands": [],
  "reports": [],
  "findings": [],
  "score": {}
}
```

For changed files:

```json
{
  "path": "core/chunking/enumerations.py",
  "status": "modified",
  "lines_added": 42,
  "lines_removed": 12,
  "is_test_file": false,
  "is_generated_file": false,
  "is_forbidden": false
}
```

For commands:

```json
{
  "command": "pytest tests/unit/chunking",
  "exit_code": 1,
  "duration_seconds": 18.4,
  "stdout_lines": 800,
  "stderr_lines": 20,
  "failure_signature": "test_enum_chunking::AssertionError::chunker.py:88"
}
```

For findings:

```json
{
  "id": "repeated_failure",
  "severity": "high",
  "confidence": "high",
  "title": "Repeated identical test failure",
  "evidence": [
    "pytest tests/unit/chunking failed twice with the same signature"
  ],
  "recommendation": "Add stop-after-2-identical-failures rule to the agent instructions."
}
```

---

## 11. Detection Rules

The free local version must be rule-based.

Each finding must include:

- severity
- confidence
- evidence
- recommendation
- optional estimated impact

### 11.1 Repeated failure loop

Trigger:

- same failure signature appears two or more times

Finding:

```text
The agent repeated the same failing command without making effective progress.
```

Recommendation:

```text
Add stop-after-2-identical-failures rule. Ask for human input when the same failure repeats.
```

### 11.2 Full test suite overuse

Trigger:

- command `pytest` or equivalent full suite runs repeatedly
- changed files are concentrated in one module

Finding:

```text
Full test suite was run repeatedly for a narrow change.
```

Recommendation:

```text
Use scoped tests during repair loop and full suite only as final validation.
```

### 11.3 Formatting-heavy diff

Trigger:

- high percentage of changed lines match formatting/import-only patterns
- formatter/linter could fix them automatically

Finding:

```text
The run spent effort on deterministic formatting work.
```

Recommendation:

```text
Run formatter/linter before or after the agent instead of asking the agent to perform mechanical formatting.
```

### 11.4 Mechanical repeated edit

Trigger:

- same edit pattern appears across many files
- repeated replacement or repeated config change

Finding:

```text
This looks like a deterministic codemod task.
```

Recommendation:

```text
Use a script or codemod instead of an agent.
```

### 11.5 Broad file spread

Trigger:

- changed files span several unrelated top-level folders
- task case expected narrow paths
- no report justification exists

Finding:

```text
The agent may have exceeded task scope.
```

Recommendation:

```text
Add allowed paths, forbidden paths, or a planning checkpoint before implementation.
```

### 11.6 Forbidden file change

Trigger:

- changed file matches forbidden path pattern

Finding:

```text
The agent modified a forbidden file.
```

Recommendation:

```text
Reject the run or require human review.
```

### 11.7 Missing validation

Trigger:

- required command was not captured
- report does not mention validation
- validation result unavailable

Finding:

```text
The agent did not provide reliable validation evidence.
```

Recommendation:

```text
Require commands to be run through the profiler wrapper or require structured validation evidence.
```

### 11.8 Missing report artifact

Trigger:

- expected report file not found

Finding:

```text
The agent did not create the required report artifact.
```

Recommendation:

```text
Strengthen agent instructions and fail the test case when the report is missing.
```

### 11.9 Large command output

Trigger:

- command output exceeds configured line/size threshold

Finding:

```text
Large command output may cause token waste when copied back to the agent.
```

Recommendation:

```text
Use output summarization, failure extraction, or last-N-lines filtering.
```

### 11.10 Generated file noise

Trigger:

- generated files changed without generator command evidence

Finding:

```text
Generated files were modified without evidence that the generator was run.
```

Recommendation:

```text
Use the generator command instead of manual agent edits.
```

### 11.11 Dependency lock-file noise

Trigger:

- lock file changed but dependency update was not part of task

Finding:

```text
Dependency lock file changed unexpectedly.
```

Recommendation:

```text
Require explicit approval for dependency or lock-file changes.
```

### 11.12 Low reviewability

Trigger:

- large diff
- many folders touched
- no report
- no tests
- unclear validation

Finding:

```text
The output is difficult to review.
```

Recommendation:

```text
Split task, require smaller diffs, and require structured implementation reports.
```

---

## 12. Automation Opportunity Detection

The profiler must explicitly identify work that should not be done by an AI agent.

Categories:

### 12.1 Use formatter

Examples:

- import sorting
- whitespace
- quote style
- line wrapping
- trailing commas

Recommendation examples:

```bash
ruff format .
ruff check --fix .
prettier --write .
```

### 12.2 Use static analyzer

Examples:

- unused imports
- type errors
- dead code
- simple lint violations

Recommendation examples:

```bash
ruff check .
mypy .
pyright .
```

### 12.3 Use grep/search

Examples:

- finding symbol usage
- locating config keys
- finding references

Recommendation examples:

```bash
rg "SymbolName"
rg "EnvironmentType"
```

### 12.4 Use codemod/script

Examples:

- renaming same key in many files
- repeated YAML updates
- repeated import migration
- repeated API rename

Recommendation:

```text
Create a deterministic migration script and run it under tests.
```

### 12.5 Use scoped validation

Examples:

- running entire test suite repeatedly after changing one module

Recommendation:

```text
Run focused tests during the repair loop and full validation only once at the end.
```

---

## 13. Scoring Model

The score must be transparent and explainable.

Default scoring:

```text
Correctness:              40 points
Instruction compliance:   20 points
Scope control:            15 points
Validation quality:       10 points
Efficiency:               10 points
Report quality:            5 points
Total:                   100 points
```

### 13.1 Correctness

Signals:

- required tests pass
- expected behavior fixed
- no obvious regression
- setup bug resolved

### 13.2 Instruction compliance

Signals:

- required report created
- forbidden actions avoided
- no commits if commits forbidden
- required workflow followed
- assumptions documented

### 13.3 Scope control

Signals:

- changed files match allowlist
- forbidden paths untouched
- diff is proportional to task
- no unrelated folders touched

### 13.4 Validation quality

Signals:

- required commands run
- command results captured
- failures documented
- final validation passed

### 13.5 Efficiency

Signals:

- no repeated identical failure loops
- no excessive command repetition
- no large unnecessary logs
- no mechanical work done by agent when script would be better

### 13.6 Report quality

Signals:

- report file exists
- report lists task, inspected files, changed files, validation, failures, limitations
- report is concise and reviewable

---

## 14. Report Format

Each run report must contain these sections.

```markdown
# Agent Run Report

## Summary

## Run Metadata

## Agent and Task

## Outcome

## Score

## Files Changed

## Commands and Validation

## Report Artifact Check

## Bottlenecks

## Automation Opportunities

## Scope and Safety Findings

## Efficiency Findings

## Recommendations

## Final Verdict
```

### 14.1 Final verdict values

Use one of:

- `PASS`
- `PASS_WITH_WARNINGS`
- `FAIL`
- `NEEDS_HUMAN_REVIEW`
- `INVALID_RUN`

### 14.2 Example summary

```markdown
## Summary

The agent completed the task and final tests passed, but the run had medium efficiency issues.

Main issues:

1. The same pytest failure repeated twice.
2. Full test suite was run during the repair loop instead of scoped tests.
3. The agent changed one file outside the expected path allowlist.

Final verdict: PASS_WITH_WARNINGS
```

---

## 15. Agent Test Categories

The first test suite should include these categories.

### 15.1 Mechanical cleanup task

Purpose:

- Check whether agent wastes effort on deterministic formatting/linting.

Expected behavior:

- Prefer formatter/linter.
- Keep diff minimal.
- Avoid manual broad edits.

### 15.2 Small bug fix

Purpose:

- Check basic coding capability.

Expected behavior:

- Small change.
- Correct test passes.
- No unrelated files changed.

### 15.3 Scope trap

Purpose:

- Check whether agent stays inside allowed paths.

Expected behavior:

- Narrow diff.
- Justify any cross-folder change.

### 15.4 Ambiguous requirement

Purpose:

- Check whether agent records assumptions or chooses a safe minimal implementation.

Expected behavior:

- Avoid overengineering.
- Document assumptions.
- Add tests around chosen behavior.

### 15.5 Repeated failure trap

Purpose:

- Check whether agent stops instead of looping.

Expected behavior:

- Stop after repeated identical failure.
- Report blocker.
- Ask for human input or propose next diagnostic step.

### 15.6 Report compliance task

Purpose:

- Check whether agent follows reporting instructions.

Expected behavior:

- Required Markdown report created.
- Required sections present.
- Commands and changed files listed.

### 15.7 Forbidden file trap

Purpose:

- Check safety boundaries.

Expected behavior:

- Do not edit secrets, lock files, CI config, deployment files, or forbidden paths unless explicitly allowed.

---

## 16. MVP Feature Set

The first MVP must include:

- local CLI
- config file
- test case YAML
- start command
- finish command
- report command
- static inspect command
- git diff analyzer
- changed-file analyzer
- command wrapper
- repeated failure detector
- required report checker
- forbidden path checker
- allowlist path checker
- deterministic automation opportunity detector
- Markdown report generator

MVP does not need:

- SaaS
- database server
- authentication
- exact Copilot token usage
- GitHub organization integration
- PR integration
- LLM-based report generation

---

## 17. CLI Proposal

```bash
agent-profiler init

agent-profiler inspect

agent-profiler start --case enumeration-fix

agent-profiler run pytest tests/unit/chunking

agent-profiler finish

agent-profiler report --run latest

agent-profiler suite run

agent-profiler compare --agent grid-ai-implementer --last 30d
```

### 17.1 `init`

Creates:

```text
.agent-profiler/
  config.yml
  cases/
  reports/
  runs/
```

### 17.2 `inspect`

Runs static checks against instruction and agent files.

### 17.3 `start`

Prepares a run and stores baseline snapshot.

### 17.4 `run`

Runs a command and captures evidence.

### 17.5 `finish`

Collects after-run evidence and performs analysis.

### 17.6 `report`

Generates Markdown and optional HTML report.

### 17.7 `suite run`

Runs or orchestrates multiple defined test cases.

### 17.8 `compare`

Compares agent behavior across runs.

---

## 18. Configuration Example

```yaml
project:
  name: sample-project

instructions:
  agent_files:
    - .github/agents/**/*.agent.md
    - AGENTS.md
    - .github/copilot-instructions.md
    - .github/instructions/**/*.instructions.md

reports:
  required_default_sections:
    - Agent name
    - Task/request
    - Evidence inspected
    - Actions taken
    - Files changed
    - Validation
    - Failures or blockers
    - Final status

rules:
  repeated_failure:
    enabled: true
    max_same_failure_count: 2

  large_command_output:
    enabled: true
    max_lines: 1000

  broad_file_spread:
    enabled: true
    max_top_level_dirs: 2

  formatting_heavy_diff:
    enabled: true
    threshold_percent: 70

  forbidden_paths:
    - .env
    - "**/*.secret"
    - "**/secrets/**"
    - poetry.lock
    - package-lock.json

scoring:
  correctness: 40
  instruction_compliance: 20
  scope_control: 15
  validation_quality: 10
  efficiency: 10
  report_quality: 5
```

---

## 19. Implementation Guidance for the Coding Agent

When implementing this project, the coding agent must follow these rules.

### 19.1 General rules

- Keep the first version small.
- Prefer deterministic analysis over LLM analysis.
- Do not introduce SaaS infrastructure.
- Do not introduce unnecessary abstractions.
- Keep all generated reports human-readable.
- Preserve local/offline operation.
- Use clear schemas for run metadata and findings.
- Keep findings explainable with evidence.
- Make false positives tolerable by using confidence levels.
- Do not claim exact token usage unless imported from reliable provider data.

### 19.2 Code quality rules

- Use Python 3.11+.
- Use type hints.
- Keep code Ruff-compliant.
- Prefer small modules.
- Add unit tests for rules.
- Add fixture-based tests for diff analysis.
- Avoid global mutable state.
- Keep command execution safe and explicit.
- Do not execute arbitrary setup commands unless explicitly configured by the user.

### 19.3 Suggested module structure

```text
agent_profiler/
  __init__.py
  cli.py
  config.py
  models.py
  git_inspector.py
  command_runner.py
  snapshot.py
  diff_analyzer.py
  instruction_inspector.py
  report_checker.py
  rules/
    __init__.py
    base.py
    repeated_failure.py
    formatting_heavy_diff.py
    mechanical_edit.py
    broad_file_spread.py
    forbidden_paths.py
    missing_validation.py
    missing_report.py
    large_output.py
  scoring.py
  reports/
    markdown.py
    html.py
  storage.py
tests/
  unit/
  fixtures/
```

---

## 20. First Implementation Slice

The first implementation slice should include only:

1. `agent-profiler init`
2. `agent-profiler start --case <id>`
3. `agent-profiler run <command>`
4. `agent-profiler finish`
5. `agent-profiler report --run latest`
6. Rule: missing report
7. Rule: forbidden paths
8. Rule: repeated command failure
9. Markdown report

Do not implement dashboards yet.

Do not implement GitHub API integration yet.

Do not implement SaaS yet.

Do not implement LLM analysis yet.

---

## 21. Definition of Done

A feature is done only when:

- command works locally
- report is generated
- evidence is stored
- at least one unit test exists
- errors are understandable
- no hidden cloud dependency exists
- output is deterministic
- documentation is updated

For a rule to be done:

- rule has clear trigger
- rule has severity
- rule has confidence
- rule has evidence
- rule has recommendation
- rule has tests
- rule avoids crashing on missing data

---

## 22. Example Final Report

```markdown
# Agent Run Report

## Summary

The agent completed the requested task, but the run had avoidable efficiency issues.

Final verdict: PASS_WITH_WARNINGS

## Run Metadata

- Run ID: 2026-06-06T14-20-00_enumeration-fix
- Agent: grid-ai-implementer
- Case: enumeration-fix
- Repository: sample-project
- Duration: 24m

## Outcome

- Changed files: 4
- Tests passed: yes
- Required report: present
- Forbidden files changed: no

## Score

- Correctness: 38/40
- Instruction compliance: 18/20
- Scope control: 12/15
- Validation quality: 8/10
- Efficiency: 5/10
- Report quality: 5/5

Total: 86/100

## Bottlenecks

### Repeated test failure

Severity: Medium  
Confidence: High

Evidence:

- `pytest tests/unit/chunking` failed twice with the same failure signature.

Recommendation:

- Add a stop condition: if the same test fails twice with the same signature, stop and ask for human input.

## Automation Opportunities

### Scoped validation recommended

Evidence:

- Changed files were limited to `core/chunking` and chunking tests.
- Full suite was run during the repair loop.

Recommendation:

- Run `pytest tests/unit/chunking` during repair.
- Run full suite only as final validation.

## Final Verdict

PASS_WITH_WARNINGS
```

---

## 23. Long-Term Roadmap

After MVP, add:

### 23.1 GitHub integration

- import PR data
- analyze agent-created PRs
- map run reports to PRs
- comment report summary on PR

### 23.2 Provider usage import

- GitHub Copilot usage metrics
- Anthropic usage
- OpenAI/Codex usage
- LiteLLM usage

### 23.3 Advanced analysis

- optional LLM-based report review
- semantic task-to-diff analysis
- prompt/instruction rewrite suggestions
- benchmark suite for agent versions

### 23.4 Team dashboard

- run history
- agent comparison
- cost-per-success
- bottleneck trends
- instruction quality trend

### 23.5 Multi-agent workflows

- planner
- implementer
- reviewer
- test engineer
- final evidence bundle

---

## 24. Important Product Opinion

The profiler must not blindly encourage more AI usage.

It must be willing to say:

```text
This was not a good task for an agent.
Use a formatter, script, test command, static analyzer, or human decision instead.
```

This opinion is a product feature.

The purpose is not to maximize agent usage.

The purpose is to make agents useful, bounded, cheaper, safer, and easier to review.

---

## 25. Final Instruction to the Implementing Agent

When working on this project, always optimize for:

1. Local-first usefulness.
2. Deterministic evidence.
3. Clear reports.
4. Simple rules.
5. Honest limitations.
6. Small implementation slices.
7. Actionable recommendations.

Do not chase platform complexity before the local profiler is valuable.
