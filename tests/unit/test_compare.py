from __future__ import annotations

from pathlib import Path

from agent_profiler.cli import main
from agent_profiler.models import Finding, RunMetadata, UsageMetadata
from agent_profiler.reports.comparison import render_comparison_report
from agent_profiler.storage import ensure_layout, save_run


def test_render_comparison_report_summarizes_runs() -> None:
    runs = [
        _run("run-1", "PASS", 100, "agent-a", "case-a", estimated_cost=0.5),
        _run(
            "run-2",
            "PASS_WITH_WARNINGS",
            80,
            "agent-a",
            "case-b",
            finding_id="missing_tests",
            estimated_cost=1.5,
        ),
        _run(
            "run-3",
            "NEEDS_HUMAN_REVIEW",
            60,
            "agent-b",
            "case-b",
            finding_id="missing_tests",
            estimated_cost=2.5,
        ),
    ]

    report = render_comparison_report(runs)

    assert "# Agent Profiler Comparison Report" in report
    assert "- Run count: 3" in report
    assert "- Average score: 80.0/100" in report
    assert "- Average cost per run: 1.5000" in report
    assert "- Average cost per valid run: 1.5000" in report
    assert "- PASS: 1" in report
    assert "- missing_tests: 2 (Missing Tests)" in report
    assert "## Repeated Bottlenecks" in report
    assert "- agent-a: 2" in report
    assert "- case-b: 2" in report
    assert "- case-b: 4.0000" in report
    assert "- Add tests.: 2" in report
    assert "## Most Common Optimization Suggestions" in report
    assert "- Ask the agent to add or justify focused tests.: 2" in report


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


def test_compare_command_valid_only_excludes_invalid_runs(tmp_path: Path, monkeypatch) -> None:
    ensure_layout(tmp_path)
    save_run(tmp_path, _run("run-1", "PASS", 100, "agent-a", "case-a"))
    save_run(tmp_path, _run("run-2", "INVALID_RUN", 0, "agent-b", "case-b"))
    save_run(
        tmp_path,
        _run(
            "run-3",
            "PASS_WITH_WARNINGS",
            75,
            "agent-c",
            "case-c",
            finding_id="missing_tests",
        ),
    )
    monkeypatch.chdir(tmp_path)

    assert main(["compare", "--last", "3", "--valid-only"]) == 0

    reports = list((tmp_path / ".agent-profiler" / "reports").glob("comparison-*.md"))
    assert len(reports) == 1
    report_text = reports[0].read_text(encoding="utf-8")
    assert "- Run count: 2" in report_text
    assert "- Invalid runs excluded: 1" in report_text
    assert "INVALID_RUN" not in report_text
    assert "run-2" not in report_text


def test_comparison_report_includes_cost_recommendations() -> None:
    runs = [
        _run(
            "run-1",
            "INVALID_RUN",
            0,
            "agent-a",
            "case-a",
            finding_id="expensive_invalid_run",
            recommendation="Stop invalid runs earlier.",
            estimated_cost=3.0,
        )
    ]

    report = render_comparison_report(runs)

    assert "- Invalid-run estimated waste: 3.0000" in report
    assert "## Cost-Related Recommendations" in report
    assert "- Stop invalid runs earlier.: 1" in report


def _run(
    run_id: str,
    verdict: str,
    total_score: int,
    agent: str,
    case_id: str,
    *,
    finding_id: str | None = None,
    recommendation: str = "Add tests.",
    estimated_cost: float | None = None,
) -> RunMetadata:
    finding = (
        Finding(
            id=finding_id,
            severity="medium",
            confidence="high",
            title=finding_id.replace("_", " ").title(),
            evidence=["evidence"],
            recommendation=recommendation,
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
        usage=UsageMetadata("provider", "model", estimated_cost=estimated_cost)
        if estimated_cost is not None
        else None,
        verdict=verdict,
    )
