from __future__ import annotations

from pathlib import Path

from agent_profiler.models import Finding, RunMetadata


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
        *_grouped_finding_lines(run),
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
        *_finding_lines(run, _CATEGORY_IDS["automation opportunities"]),
        "",
        "## Scope and Safety Findings",
        "",
        *_finding_lines(run, _CATEGORY_IDS["scope"] | _CATEGORY_IDS["safety"]),
        "",
        "## Efficiency Findings",
        "",
        *_finding_lines(run, _CATEGORY_IDS["efficiency"]),
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


_CATEGORY_IDS = {
    "scope": {
        "broad_file_spread",
        "missing_tests",
        "low_reviewability",
    },
    "validation": {
        "missing_report",
        "repeated_failure",
        "full_test_suite_overuse",
        "missing_tests",
    },
    "efficiency": {
        "repeated_failure",
        "large_command_output",
        "full_test_suite_overuse",
        "low_reviewability",
    },
    "automation opportunities": {
        "formatting_heavy_diff",
        "mechanical_repeated_edit",
        "generated_file_changed_manually",
    },
    "safety": {
        "forbidden_file_changed",
        "lock_file_changed_unexpectedly",
        "generated_file_changed_manually",
    },
}


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


def _grouped_finding_lines(run: RunMetadata) -> list[str]:
    if not run.findings:
        return ["No MVP rule findings."]
    lines: list[str] = []
    emitted: set[str] = set()
    for category, ids in _CATEGORY_IDS.items():
        category_findings = [finding for finding in run.findings if finding.id in ids]
        lines.extend([f"### {category.title()}", ""])
        if not category_findings:
            lines.extend(["None.", ""])
            continue
        for finding in category_findings:
            emitted.add(finding.id)
            lines.extend(_finding_detail_lines(finding))
    uncategorized = [finding for finding in run.findings if finding.id not in emitted]
    if uncategorized:
        lines.extend(["### Other", ""])
        for finding in uncategorized:
            lines.extend(_finding_detail_lines(finding))
    return lines


def _finding_detail_lines(finding: Finding) -> list[str]:
    return [
        f"#### {finding.title}",
        "",
        f"- ID: {finding.id}",
        f"- Severity: {finding.severity}",
        f"- Confidence: {finding.confidence}",
        f"- Evidence: {'; '.join(finding.evidence)}",
        f"- Recommendation: {finding.recommendation}",
        "",
    ]


def _recommendation_lines(run: RunMetadata) -> list[str]:
    if not run.findings:
        return ["No MVP rule recommendations."]
    return [f"- {finding.recommendation}" for finding in run.findings]
