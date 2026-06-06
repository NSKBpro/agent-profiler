from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from agent_profiler.models import Finding, RunMetadata


def analyze_run(root: Path, run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_missing_required_reports(root, run))
    findings.extend(_forbidden_file_changes(run))
    findings.extend(_repeated_command_failures(run, config))
    findings.extend(_large_command_outputs(run, config))
    return findings


def _missing_required_reports(root: Path, run: RunMetadata) -> list[Finding]:
    required = run.case.get("validation", {}).get("required_reports", [])
    missing = [str(path) for path in required if not (root / str(path)).exists()]
    if not missing:
        return []
    return [
        Finding(
            id="missing_report",
            severity="high",
            confidence="high",
            title="Required report artifact is missing",
            evidence=[f"Missing required report: {path}" for path in missing],
            recommendation=(
                "Require the agent to create the expected Markdown report before finish."
            ),
        )
    ]


def _forbidden_file_changes(run: RunMetadata) -> list[Finding]:
    forbidden = [
        changed_file.path for changed_file in run.changed_files if changed_file.is_forbidden
    ]
    if not forbidden:
        return []
    return [
        Finding(
            id="forbidden_file_changed",
            severity="high",
            confidence="high",
            title="Forbidden file changed",
            evidence=[f"Forbidden path changed: {path}" for path in forbidden],
            recommendation="Reject the run or require human review for forbidden path changes.",
        )
    ]


def _repeated_command_failures(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    rule = config.get("rules", {}).get("repeated_failure", {})
    if not rule.get("enabled", True):
        return []
    threshold = int(rule.get("max_same_failure_count", 2))
    signatures = [
        command.failure_signature
        for command in run.commands
        if command.exit_code != 0 and command.failure_signature
    ]
    counts = Counter(signatures)
    repeated = {signature: count for signature, count in counts.items() if count >= threshold}
    if not repeated:
        return []
    evidence = [
        f"Failure signature repeated {count} times: {signature}"
        for signature, count in sorted(repeated.items())
    ]
    return [
        Finding(
            id="repeated_failure",
            severity="high",
            confidence="high",
            title="Repeated identical command failure",
            evidence=evidence,
            recommendation=(
                "Stop after repeated identical failures and ask for human input or change "
                "diagnostics."
            ),
        )
    ]


def _large_command_outputs(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    rule = config.get("rules", {}).get("large_command_output", {})
    if not rule.get("enabled", True):
        return []
    max_lines = int(rule.get("max_lines", 1000))
    oversized = [
        command
        for command in run.commands
        if command.stdout_lines + command.stderr_lines > max_lines
    ]
    if not oversized:
        return []
    return [
        Finding(
            id="large_command_output",
            severity="medium",
            confidence="high",
            title="Large command output captured",
            evidence=[
                f"`{command.command}` produced {command.stdout_lines + command.stderr_lines} lines"
                for command in oversized
            ],
            recommendation="Use focused commands, output summarization, or last-N-lines filtering.",
        )
    ]
