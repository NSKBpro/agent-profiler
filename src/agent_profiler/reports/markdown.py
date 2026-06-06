from __future__ import annotations

from pathlib import Path

from agent_profiler.models import RunMetadata


def write_markdown_report(root: Path, run: RunMetadata) -> Path:
    path = root / ".agent-profiler" / "reports" / f"{run.path_safe_id}.md"
    path.write_text(render_markdown_report(run), encoding="utf-8")
    return path


def render_markdown_report(run: RunMetadata) -> str:
    lines = [
        "# Agent Run Report",
        "",
        "## Summary",
        "",
        _summary(run),
        "",
        "## Run Metadata",
        "",
        f"- Run ID: {run.run_id}",
        f"- Case: {run.case_id or 'none'}",
        f"- Agent: {run.agent or 'unknown'}",
        f"- Repository: {run.repo_path}",
        f"- Started: {run.started_at}",
        f"- Finished: {run.finished_at or 'not finished'}",
        f"- Final verdict: {run.verdict}",
        "",
        "## Task and Agent",
        "",
        f"- Title: {run.case.get('title', 'not specified')}",
        f"- Task prompt: {run.case.get('task_prompt', 'not specified')}",
        f"- Agent: {run.agent or 'unknown'}",
        "",
        "## Outcome",
        "",
        f"- Changed files: {len(run.changed_files)}",
        f"- Commands captured: {len(run.commands)}",
        f"- Findings: {len(run.findings)}",
        "",
        "## Score",
        "",
        *_score_lines(run),
        "",
        "## Changed Files",
        "",
        *_changed_file_lines(run),
        "",
        "## Commands Run",
        "",
        *_command_lines(run),
        "",
        "## Findings",
        "",
        *_all_finding_lines(run),
        "",
        "## Report Artifact Check",
        "",
        *_report_lines(run),
        "",
        "## Bottlenecks",
        "",
        *_finding_lines(run, {"repeated_failure", "large_command_output"}),
        "",
        "## Automation Opportunities",
        "",
        "No deterministic automation opportunities beyond captured rule findings were detected.",
        "",
        "## Scope and Safety Findings",
        "",
        *_finding_lines(run, {"forbidden_file_changed", "missing_report"}),
        "",
        "## Efficiency Findings",
        "",
        *_finding_lines(run, {"repeated_failure", "large_command_output"}),
        "",
        "## Recommendations",
        "",
        *_recommendation_lines(run),
        "",
        "## Final Verdict",
        "",
        run.verdict,
        "",
    ]
    return "\n".join(lines)


def _summary(run: RunMetadata) -> str:
    if not run.findings:
        return f"The run completed with no MVP rule findings. Final verdict: {run.verdict}."
    titles = "; ".join(finding.title for finding in run.findings)
    return f"The run completed with findings: {titles}. Final verdict: {run.verdict}."


def _score_lines(run: RunMetadata) -> list[str]:
    lines = [f"- {name.replace('_', ' ').title()}: {value}" for name, value in run.score.items()]
    lines.append(f"- Total: {sum(run.score.values())}")
    return lines


def _changed_file_lines(run: RunMetadata) -> list[str]:
    if not run.changed_files:
        return ["No changed files detected."]
    return [
        (
            f"- {item.path} ({item.status}, +{item.lines_added}/-{item.lines_removed}"
            f"{', forbidden' if item.is_forbidden else ''})"
        )
        for item in run.changed_files
    ]


def _command_lines(run: RunMetadata) -> list[str]:
    if not run.commands:
        return ["No commands were captured through `agent-profiler run`."]
    return [
        (
            f"- `{command.command}` exited {command.exit_code} in "
            f"{command.duration_seconds:.2f}s; output: {command.output_path}"
        )
        for command in run.commands
    ]


def _report_lines(run: RunMetadata) -> list[str]:
    required = run.case.get("validation", {}).get("required_reports", [])
    if not required:
        return ["No required report artifacts configured for this case."]
    return [f"- {path}: {'present' if path in run.reports else 'missing'}" for path in required]


def _finding_lines(run: RunMetadata, ids: set[str]) -> list[str]:
    findings = [finding for finding in run.findings if finding.id in ids]
    if not findings:
        return ["None."]
    lines: list[str] = []
    for finding in findings:
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"- Severity: {finding.severity}",
                f"- Confidence: {finding.confidence}",
                f"- Evidence: {'; '.join(finding.evidence)}",
                f"- Recommendation: {finding.recommendation}",
                "",
            ]
        )
    return lines


def _all_finding_lines(run: RunMetadata) -> list[str]:
    if not run.findings:
        return ["No MVP rule findings."]
    lines: list[str] = []
    for finding in run.findings:
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"- ID: {finding.id}",
                f"- Severity: {finding.severity}",
                f"- Confidence: {finding.confidence}",
                f"- Evidence: {'; '.join(finding.evidence)}",
                f"- Recommendation: {finding.recommendation}",
                "",
            ]
        )
    return lines


def _recommendation_lines(run: RunMetadata) -> list[str]:
    if not run.findings:
        return ["No MVP rule recommendations."]
    return [f"- {finding.recommendation}" for finding in run.findings]
