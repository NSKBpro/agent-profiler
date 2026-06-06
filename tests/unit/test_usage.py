from __future__ import annotations

from pathlib import Path

from agent_profiler.cli import main
from agent_profiler.models import ChangedFile, RunMetadata, UsageMetadata
from agent_profiler.reports.markdown import render_markdown_report
from agent_profiler.rules import analyze_run
from agent_profiler.storage import ensure_layout, load_run, save_run


def test_attach_usage_command_copies_usage_and_updates_run(tmp_path: Path, monkeypatch) -> None:
    ensure_layout(tmp_path)
    save_run(tmp_path, _run("run-1"))
    usage_file = tmp_path / "usage.yml"
    usage_file.write_text(
        "\n".join(
            [
                "provider: test-provider",
                "model: test-model",
                "estimated_cost: 0.75",
                "input_tokens: 100",
                "output_tokens: 150",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert main(["attach-usage", "--run", "latest", "--file", str(usage_file)]) == 0

    run = load_run(tmp_path, "latest")
    assert run.usage is not None
    assert run.usage.provider == "test-provider"
    assert run.usage_path == ".agent-profiler/usage/run-1.yml"
    assert (tmp_path / ".agent-profiler" / "usage" / "run-1.yml").is_file()


def test_expensive_invalid_run_rule_works(tmp_path: Path) -> None:
    run = _run(
        "run-1", verdict="INVALID_RUN", usage=UsageMetadata("provider", "model", estimated_cost=1.5)
    )

    assert "expensive_invalid_run" in _finding_ids(tmp_path, run)


def test_high_cost_low_change_rule_works(tmp_path: Path) -> None:
    run = _run(
        "run-1",
        changed_files=[ChangedFile("src/a.py", "modified", lines_added=2)],
        usage=UsageMetadata("provider", "model", estimated_cost=0.75),
    )

    assert "high_cost_low_change" in _finding_ids(tmp_path, run)


def test_high_output_token_ratio_rule_works(tmp_path: Path) -> None:
    run = _run(
        "run-1",
        usage=UsageMetadata("provider", "model", input_tokens=100, output_tokens=150),
    )

    assert _finding_ids(tmp_path, run) == {"high_output_token_ratio"}


def test_expensive_docs_only_run_rule_works(tmp_path: Path) -> None:
    run = _run(
        "run-1",
        changed_files=[ChangedFile("README.md", "modified")],
        usage=UsageMetadata("provider", "model", estimated_cost=0.5),
    )

    assert _finding_ids(tmp_path, run) == {"expensive_docs_only_run", "high_cost_low_change"}


def test_run_report_includes_usage_and_cost_sections() -> None:
    run = _run(
        "run-1",
        changed_files=[ChangedFile("README.md", "modified")],
        usage=UsageMetadata(
            "provider",
            "model",
            agent="agent",
            input_tokens=100,
            output_tokens=150,
            estimated_cost=0.5,
            duration_seconds=60,
        ),
    )
    run.findings = analyze_run(Path("."), run, {"rules": {}})

    report = render_markdown_report(run)

    assert "## Usage and Cost" in report
    assert "## Cost Efficiency" in report
    assert "## Usage Optimization Suggestions" in report
    assert "- Estimated cost: 0.5000" in report
    assert "Use cheaper deterministic checks for docs-only changes." in report


def _finding_ids(tmp_path: Path, run: RunMetadata) -> set[str]:
    return {finding.id for finding in analyze_run(tmp_path, run, {"rules": {}})}


def _run(
    run_id: str,
    *,
    verdict: str = "PASS",
    changed_files: list[ChangedFile] | None = None,
    usage: UsageMetadata | None = None,
) -> RunMetadata:
    return RunMetadata(
        run_id=run_id,
        case_id="case-1",
        agent="agent",
        repo_path="repo",
        started_at="2026-06-06T00:00:00+00:00",
        changed_files=changed_files or [],
        usage=usage,
        score={"total": 100},
        verdict=verdict,
    )
