from __future__ import annotations

from pathlib import Path

from agent_profiler.models import ChangedFile, CommandRecord, RunMetadata
from agent_profiler.rules import analyze_run


def test_missing_report_rule_works(tmp_path: Path) -> None:
    run = RunMetadata(
        run_id="run-1",
        case_id="case-1",
        agent="agent",
        repo_path=str(tmp_path),
        started_at="2026-06-06T00:00:00+00:00",
        case={"validation": {"required_reports": ["missing.md"]}},
    )

    findings = analyze_run(tmp_path, run, {"rules": {}})

    assert {finding.id for finding in findings} == {"missing_report"}


def test_forbidden_path_rule_works(tmp_path: Path) -> None:
    run = RunMetadata(
        run_id="run-1",
        case_id="case-1",
        agent="agent",
        repo_path=str(tmp_path),
        started_at="2026-06-06T00:00:00+00:00",
        changed_files=[ChangedFile(path=".env", status="modified", is_forbidden=True)],
    )

    findings = analyze_run(tmp_path, run, {"rules": {}})

    assert {finding.id for finding in findings} == {"forbidden_file_changed"}


def test_repeated_failure_rule_works(tmp_path: Path) -> None:
    run = RunMetadata(
        run_id="run-1",
        case_id="case-1",
        agent="agent",
        repo_path=str(tmp_path),
        started_at="2026-06-06T00:00:00+00:00",
        commands=[
            _command("pytest", 1, 10, "same failure"),
            _command("pytest", 1, 10, "same failure"),
        ],
    )

    findings = analyze_run(
        tmp_path,
        run,
        {
            "rules": {
                "repeated_failure": {"enabled": True, "max_same_failure_count": 2},
            }
        },
    )

    assert {finding.id for finding in findings} == {"repeated_failure"}


def test_large_command_output_rule_works(tmp_path: Path) -> None:
    run = RunMetadata(
        run_id="run-1",
        case_id="case-1",
        agent="agent",
        repo_path=str(tmp_path),
        started_at="2026-06-06T00:00:00+00:00",
        commands=[_command("pytest", 0, 1200, "")],
    )

    findings = analyze_run(
        tmp_path,
        run,
        {"rules": {"large_command_output": {"enabled": True, "max_lines": 1000}}},
    )

    assert {finding.id for finding in findings} == {"large_command_output"}


def _command(command: str, exit_code: int, lines: int, signature: str) -> CommandRecord:
    return CommandRecord(
        command=command,
        working_directory=".",
        started_at="2026-06-06T00:00:00+00:00",
        ended_at="2026-06-06T00:00:01+00:00",
        duration_seconds=1.0,
        exit_code=exit_code,
        stdout_lines=lines,
        stderr_lines=0,
        stdout_bytes=0,
        stderr_bytes=0,
        output_path=".agent-profiler/runs/run-1/command-001.log",
        failure_signature=signature,
    )
