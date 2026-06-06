from __future__ import annotations

from agent_profiler.models import Finding, RunMetadata
from agent_profiler.reports.markdown import render_markdown_report


def test_markdown_report_contains_required_sections() -> None:
    run = RunMetadata(
        run_id="run-1",
        case_id="case-1",
        agent="agent",
        repo_path="repo",
        started_at="2026-06-06T00:00:00+00:00",
        finished_at="2026-06-06T00:01:00+00:00",
        findings=[
            Finding(
                id="missing_report",
                severity="high",
                confidence="high",
                title="Required report artifact is missing",
                evidence=["Missing required report: report.md"],
                recommendation="Create the report.",
            )
        ],
        score={"correctness": 40},
        verdict="NEEDS_HUMAN_REVIEW",
    )

    report = render_markdown_report(run)

    for section in (
        "# Agent Run Report",
        "## Summary",
        "## Run Metadata",
        "## Task and Agent",
        "## Changed Files",
        "## Commands Run",
        "## Findings",
        "## Recommendations",
        "## Final Verdict",
    ):
        assert section in report
    for category in (
        "### Scope",
        "### Validation",
        "### Efficiency",
        "### Automation Opportunities",
        "### Safety",
    ):
        assert category in report
    assert "## Score" in report
    assert "NEEDS_HUMAN_REVIEW" in report
