from __future__ import annotations

from pathlib import Path

from agent_profiler.models import ChangedFile, CommandRecord, RunMetadata
from agent_profiler.rules import analyze_run


def test_formatting_heavy_diff_rule_works(tmp_path: Path) -> None:
    run = _run(
        diff="\n".join(
            [
                "+import os",
                "+import sys",
                "+",
                "+)",
                "+}",
                "+from pathlib import Path",
                "+,",
                "+(",
                "+return value",
                "+total = calculate()",
            ]
        )
    )

    assert _finding_ids(tmp_path, run) == {"formatting_heavy_diff"}


def test_mechanical_repeated_edit_rule_works(tmp_path: Path) -> None:
    run = _run(diff="+enabled = True\n+enabled = True\n+enabled = True\n")

    assert _finding_ids(tmp_path, run) == {"mechanical_repeated_edit"}


def test_broad_file_spread_rule_works(tmp_path: Path) -> None:
    run = _run(
        changed_files=[
            ChangedFile("src/a.py", "modified"),
            ChangedFile("docs/a.md", "modified"),
            ChangedFile("scripts/a.py", "modified"),
        ]
    )

    assert _finding_ids(tmp_path, run) == {"broad_file_spread", "missing_tests"}


def test_full_test_suite_overuse_rule_works(tmp_path: Path) -> None:
    run = _run(
        changed_files=[ChangedFile("src/a.py", "modified")],
        commands=[
            _command("pytest", 0),
            _command("python -m pytest", 0),
        ],
    )

    assert _finding_ids(tmp_path, run) == {"full_test_suite_overuse", "missing_tests"}


def test_lock_file_changed_unexpectedly_rule_works(tmp_path: Path) -> None:
    run = _run(changed_files=[ChangedFile("poetry.lock", "modified")])

    assert _finding_ids(tmp_path, run) == {"lock_file_changed_unexpectedly"}


def test_missing_tests_rule_works(tmp_path: Path) -> None:
    run = _run(changed_files=[ChangedFile("src/service.py", "modified")])

    assert _finding_ids(tmp_path, run) == {"missing_tests"}


def test_generated_file_changed_manually_rule_works(tmp_path: Path) -> None:
    run = _run(
        changed_files=[
            ChangedFile(
                "src/generated/client.py",
                "modified",
                is_generated_file=True,
            )
        ]
    )

    assert _finding_ids(tmp_path, run) == {"generated_file_changed_manually"}


def test_low_reviewability_rule_works(tmp_path: Path) -> None:
    run = _run(
        changed_files=[
            ChangedFile(f"src/file_{index}.py", "modified", lines_added=1) for index in range(11)
        ]
    )

    assert _finding_ids(tmp_path, run) == {
        "low_reviewability",
        "missing_tests",
    }


def _finding_ids(tmp_path: Path, run: RunMetadata) -> set[str]:
    return {finding.id for finding in analyze_run(tmp_path, run, {"rules": {}})}


def _run(
    *,
    diff: str = "",
    changed_files: list[ChangedFile] | None = None,
    commands: list[CommandRecord] | None = None,
) -> RunMetadata:
    return RunMetadata(
        run_id="run-1",
        case_id="case-1",
        agent="agent",
        repo_path="repo",
        started_at="2026-06-06T00:00:00+00:00",
        changed_files=changed_files or [],
        commands=commands or [],
        diff=diff,
    )


def _command(command: str, exit_code: int) -> CommandRecord:
    return CommandRecord(
        command=command,
        working_directory=".",
        started_at="2026-06-06T00:00:00+00:00",
        ended_at="2026-06-06T00:00:01+00:00",
        duration_seconds=1.0,
        exit_code=exit_code,
        stdout_lines=1,
        stderr_lines=0,
        stdout_bytes=1,
        stderr_bytes=0,
        output_path=".agent-profiler/runs/run-1/command-001.log",
        failure_signature=None,
    )
