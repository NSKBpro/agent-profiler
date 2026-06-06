from __future__ import annotations

from pathlib import Path

from agent_profiler.cli import main
from agent_profiler.models import Finding, RunMetadata
from agent_profiler.reports.comparison import render_comparison_report
from agent_profiler.storage import ensure_layout, save_run


def test_render_comparison_report_summarizes_runs() -> None:
    runs = [
        _run("run-1", "PASS", 100, "agent-a", "case-a"),
        _run(
            "run-2",
            "PASS_WITH_WARNINGS",
            80,
            "agent-a",
            "case-b",
            finding_id="missing_tests",
        ),
        _run(
            "run-3",
            "NEEDS_HUMAN_REVIEW",
            60,
            "agent-b",
            "case-b",
            finding_id="missing_tests",
        ),
    ]

    report = render_comparison_report(runs)

    assert "# Agent Profiler Comparison Report" in report
    assert "- Run count: 3" in report
    assert "- Average score: 80.0/100" in report
    assert "- PASS: 1" in report
    assert "- missing_tests: 2 (Missing Tests)" in report
    assert "## Repeated Bottlenecks" in report
    assert "- agent-a: 2" in report
    assert "- case-b: 2" in report
    assert "- Add tests.: 2" in report


def test_compare_command_writes_markdown_report(tmp_path: Path, monkeypatch) -> None:
    ensure_layout(tmp_path)
    save_run(tmp_path, _run("run-1", "PASS", 100, "agent-a", "case-a"))
    save_run(
        tmp_path,
        _run(
            "run-2",
            "PASS_WITH_WARNINGS",
            80,
            "agent-b",
            "case-b",
            finding_id="large_command_output",
        ),
    )
    monkeypatch.chdir(tmp_path)

    assert main(["compare", "--last", "2"]) == 0

    reports = list((tmp_path / ".agent-profiler" / "reports").glob("comparison-*.md"))
    assert len(reports) == 1
    assert "- Run count: 2" in reports[0].read_text(encoding="utf-8")


def _run(
    run_id: str,
    verdict: str,
    total_score: int,
    agent: str,
    case_id: str,
    *,
    finding_id: str | None = None,
) -> RunMetadata:
    finding = (
        Finding(
            id=finding_id,
            severity="medium",
            confidence="high",
            title=finding_id.replace("_", " ").title(),
            evidence=["evidence"],
            recommendation="Add tests.",
        )
        if finding_id
        else None
    )
    return RunMetadata(
        run_id=run_id,
        case_id=case_id,
        agent=agent,
        repo_path="repo",
        started_at="2026-06-06T00:00:00+00:00",
        findings=[finding] if finding else [],
        score={"total": total_score},
        verdict=verdict,
    )
