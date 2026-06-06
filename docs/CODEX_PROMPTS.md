# Codex Prompts

Use these prompts exactly.

---

## Prompt 1 - Full Local MVP Implementation

Paste this into Codex first.

```text
Read AGENTS.md, docs/copilot_agent_profiler_agent_contract.md, and docs/PHASES.md.

Implement the local MVP from Phase 0 through Phase 8.

Do not ask me for confirmation between phases. Continue automatically until the local MVP works end to end, unless you hit a real blocker.

Do not build:
- SaaS
- dashboard
- GitHub API integration
- PR integration
- provider usage import
- LLM/AI analysis
- Codex adapter
- Claude Code adapter
- Cursor adapter

Build a simple local Python CLI named agent-profiler.

Required commands:
1. agent-profiler init
2. agent-profiler start --case <id>
3. agent-profiler run <command>
4. agent-profiler finish
5. agent-profiler report --run latest

Required behavior:
- create .agent-profiler folder structure
- create default config
- load simple YAML test cases
- save run metadata as JSON
- capture git snapshot before and after run
- capture wrapped command execution
- analyze changed files
- detect missing required report
- detect forbidden file changes
- detect repeated command failures
- warn on large command output
- generate Markdown report
- add basic scoring
- add unit tests

Use Python 3.11+.
Keep the implementation simple.
Do not overengineer.

Run validation when possible:
- python -m pytest
- python -m ruff check .
- python -m ruff format --check .

If dependencies are missing, add minimal project configuration for them.

At the end, update:
.agent-profiler/reports/implementation-report.md

The implementation report must include:
- what was implemented
- files changed
- commands run
- validation result
- known limitations
- next recommended step

Start by creating a short plan, then implement phase by phase automatically.
```

---

## Prompt 2 - Fix MVP Until It Works

Use this if Codex stops with partial implementation.

```text
Continue from the current state.

Read:
- AGENTS.md
- docs/PHASES.md
- .agent-profiler/reports/implementation-report.md if it exists

Do not add new product scope.

Fix the local MVP until this scenario works:

1. agent-profiler init
2. create or load a sample case
3. agent-profiler start --case sample-case
4. agent-profiler run python -c "print('hello')"
5. agent-profiler finish
6. agent-profiler report --run latest

Run tests.

Update .agent-profiler/reports/implementation-report.md with:
- what was fixed
- files changed
- commands run
- validation result
- remaining limitations
```

---

## Prompt 3 - Add Phase 9 Rules

Use this only after MVP works.

```text
Read AGENTS.md and docs/PHASES.md.

The local MVP works. Now implement Phase 9 only.

Add these deterministic local rules:
1. formatting-heavy diff
2. mechanical repeated edit
3. broad file spread
4. full test suite overuse
5. lock file changed unexpectedly
6. missing tests
7. generated file changed manually
8. low reviewability

Do not add SaaS, dashboard, GitHub integration, PR integration, provider usage import, or LLM analysis.

Each rule must produce:
- ID
- severity
- confidence
- title
- evidence
- recommendation

Add tests for every rule.

Improve the Markdown report so findings are grouped by:
- scope
- validation
- efficiency
- automation opportunities
- safety

Run validation.

Update .agent-profiler/reports/implementation-report.md.
```

---

## Prompt 4 - Add Agent Comparison

Use this only after several local runs exist.

```text
Read AGENTS.md and docs/PHASES.md.

Implement Phase 10 only.

Add:

agent-profiler compare --last <number>

The command must compare recent runs and report:
- run count
- average score
- verdict counts
- most common findings
- repeated bottlenecks
- agents/cases involved
- recommendations

Generate a Markdown comparison report under:

.agent-profiler/reports/

Do not add SaaS, dashboard, GitHub integration, PR integration, provider usage import, or LLM analysis.

Add tests.

Run validation.

Update .agent-profiler/reports/implementation-report.md.
```

---

## Prompt 5 - Prepare GitHub Integration Plan Only

Use this later. Do not ask Codex to implement GitHub integration yet.

```text
Read AGENTS.md and docs/PHASES.md.

Do not implement code.

Create a plan for future GitHub integration.

The plan must describe:
- what GitHub data is needed
- what can be done without Copilot token data
- how to map PRs to agent runs
- how to attach reports to PRs
- what permissions are needed
- what should stay local
- risks and limitations

Write the plan to:

docs/GITHUB_INTEGRATION_PLAN.md
```
