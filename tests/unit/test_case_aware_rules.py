from __future__ import annotations

from pathlib import Path

from agent_profiler.models import ChangedFile, CommandRecord, RunMetadata
from agent_profiler.rules import analyze_run


def test_changed_file_outside_allowed_paths_rule_works(tmp_path: Path) -> None:
    run = _run(
        case={"expected": {"allowed_paths": ["src/**"]}},
        changed_files=[ChangedFile("docs/notes.md", "modified")],
    )

    findings = analyze_run(tmp_path, run, {"rules": {}})

    assert _finding_ids(findings) == {"changed_file_outside_allowed_paths"}


def test_missing_required_validation_command_rule_works(tmp_path: Path) -> None:
    run = _run(
        case={
            "validation": {
                "required_commands": [
                    "python -m pytest",
                    "python -m ruff check .",
                ]
            }
        },
        commands=[_command("python -m pytest")],
    )

    findings = analyze_run(tmp_path, run, {"rules": {}})

    assert _finding_ids(findings) == {"missing_required_validation_command"}
    assert findings[0].evidence == ["Missing required command: python -m ruff check ."]


def test_source_changed_without_pytest_rule_works(tmp_path: Path) -> None:
    run = _run(changed_files=[ChangedFile("src/agent_profiler/example.py", "modified")])

    findings = analyze_run(tmp_path, run, {"rules": {}})

    assert "source_changed_without_pytest" in _finding_ids(findings)


def test_docs_only_overvalidation_rule_works(tmp_path: Path) -> None:
    run = _run(
        changed_files=[ChangedFile("README.md", "modified")],
        commands=[_command("python -m pytest")],
    )

    findings = analyze_run(tmp_path, run, {"rules": {}})

    assert _finding_ids(findings) == {"docs_only_overvalidation"}


def _finding_ids(findings) -> set[str]:
    return {finding.id for finding in findings}


def _run(
    *,
    case: dict | None = None,
    changed_files: list[ChangedFile] | None = None,
    commands: list[CommandRecord] | None = None,
) -> RunMetadata:
    return RunMetadata(
        run_id="run-1",
        case_id="case-1",
        agent="agent",
        repo_path="repo",
        started_at="2026-06-06T00:00:00+00:00",
        case=case or {},
        changed_files=changed_files or [],
        commands=commands or [],
    )


def _command(command: str) -> CommandRecord:
    return CommandRecord(
        command=command,
        working_directory=".",
        started_at="2026-06-06T00:00:00+00:00",
        ended_at="2026-06-06T00:00:01+00:00",
        duration_seconds=1.0,
        exit_code=0,
        stdout_lines=1,
        stderr_lines=0,
        stdout_bytes=1,
        stderr_bytes=0,
        output_path=".agent-profiler/runs/run-1/command-001.log",
        failure_signature=None,
    )
