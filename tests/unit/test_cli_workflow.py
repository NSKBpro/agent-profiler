from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent_profiler.cli import main
from agent_profiler.config import load_case


def test_init_creates_folder_structure_and_sample_case_loads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["init"]) == 0

    profiler_dir = tmp_path / ".agent-profiler"
    for child in ("cases", "runs", "reports", "command-logs"):
        assert (profiler_dir / child).is_dir()
    assert (profiler_dir / "config.yml").is_file()

    case, case_path = load_case(tmp_path, "sample-case")
    assert case_path == profiler_dir / "cases" / "sample-case.yml"
    assert case["id"] == "sample-case"


def test_cli_workflow_creates_run_metadata_and_report(tmp_path: Path, monkeypatch) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "initial")
    monkeypatch.chdir(tmp_path)

    assert main(["init"]) == 0
    sample_case_path = tmp_path / ".agent-profiler" / "cases" / "sample-case.yml"
    sample_case_path.write_text(
        """id: sample-case
title: Sample case
agent: test-agent
task_prompt: Make a small change.
expected:
  forbidden_paths:
    - forbidden.txt
validation:
  required_reports:
    - expected-report.md
  required_commands: []
""",
        encoding="utf-8",
    )

    assert main(["start", "--case", "sample-case"]) == 0
    assert main(["run", "python", "-c", "print('ok')"]) == 0
    (tmp_path / "forbidden.txt").write_text("changed\n", encoding="utf-8")
    assert main(["finish"]) == 0
    assert main(["report", "--run", "latest"]) == 0

    reports = list((tmp_path / ".agent-profiler" / "reports").glob("*.md"))
    runs = list((tmp_path / ".agent-profiler" / "runs").glob("*.json"))
    assert reports
    assert runs
    run_data = json.loads(runs[0].read_text(encoding="utf-8"))
    assert run_data["commands"][0]["command"] == "python -c print('ok')"
    assert run_data["commands"][0]["exit_code"] == 0
    report_text = reports[0].read_text(encoding="utf-8")
    assert "Forbidden file changed" in report_text
    assert "Required report artifact is missing" in report_text


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)
