from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "project": {"name": "local-project"},
    "rules": {
        "repeated_failure": {"enabled": True, "max_same_failure_count": 2},
        "large_command_output": {"enabled": True, "max_lines": 1000},
        "forbidden_paths": [
            ".env",
            "**/*.secret",
            "**/secrets/**",
            "poetry.lock",
            "package-lock.json",
        ],
    },
    "scoring": {
        "correctness": 40,
        "instruction_compliance": 20,
        "scope_control": 15,
        "validation_quality": 10,
        "efficiency": 10,
        "report_quality": 5,
    },
}

DEFAULT_CASE: dict[str, Any] = {
    "id": "example",
    "title": "Example local agent task",
    "agent": "local-agent",
    "task_prompt": "Describe the task the coding agent should perform.",
    "expected": {
        "forbidden_paths": [".env", "**/*.secret"],
    },
    "validation": {
        "required_reports": [".agent-profiler/reports/implementation-report.md"],
    },
}

DEFAULT_SAMPLE_CASE: dict[str, Any] = {
    "id": "sample-case",
    "title": "Sample case",
    "agent": "unknown",
    "task_prompt": "Run a simple command and generate a local profiler report.",
    "expected": {
        "forbidden_paths": [".env", "**/*.secret"],
    },
    "validation": {
        "required_reports": [],
        "required_commands": [],
    },
}


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping YAML in {path}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_config(root: Path) -> dict[str, Any]:
    config_path = root / ".agent-profiler" / "config.yml"
    if not config_path.exists():
        return DEFAULT_CONFIG.copy()
    loaded = read_yaml(config_path)
    merged = DEFAULT_CONFIG.copy()
    merged.update(loaded)
    if "rules" in loaded:
        rules = DEFAULT_CONFIG["rules"].copy()
        rules.update(loaded["rules"])
        merged["rules"] = rules
    return merged


def load_case(root: Path, case_id: str) -> tuple[dict[str, Any], Path]:
    case_path = root / ".agent-profiler" / "cases" / f"{case_id}.yml"
    if not case_path.exists():
        raise FileNotFoundError(f"Test case not found: {case_path}")
    case = read_yaml(case_path)
    if str(case.get("id", "")) != case_id:
        raise ValueError(f"Case {case_path} must have id: {case_id}")
    return case, case_path
