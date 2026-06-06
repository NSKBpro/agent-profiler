from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_profiler.config import DEFAULT_CASE, DEFAULT_CONFIG, DEFAULT_SAMPLE_CASE, write_yaml
from agent_profiler.models import RunMetadata

PROFILER_DIR = ".agent-profiler"


def ensure_layout(root: Path) -> Path:
    base = root / PROFILER_DIR
    for child in ("cases", "runs", "reports", "snapshots", "command-logs"):
        (base / child).mkdir(parents=True, exist_ok=True)
    config_path = base / "config.yml"
    if not config_path.exists():
        write_yaml(config_path, DEFAULT_CONFIG)
    example_case_path = base / "cases" / "example.yml"
    if not example_case_path.exists():
        write_yaml(example_case_path, DEFAULT_CASE)
    sample_case_path = base / "cases" / "sample-case.yml"
    if not sample_case_path.exists():
        write_yaml(sample_case_path, DEFAULT_SAMPLE_CASE)
    return base


def run_path(root: Path, run_id: str) -> Path:
    return root / PROFILER_DIR / "runs" / f"{run_id}.json"


def save_run(root: Path, run: RunMetadata) -> Path:
    path = run_path(root, run.path_safe_id)
    path.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_run(root: Path, run_id: str) -> RunMetadata:
    path = resolve_run_path(root, run_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunMetadata.from_dict(data)


def resolve_run_path(root: Path, run_id: str) -> Path:
    if run_id == "latest":
        latest = latest_run_path(root)
        if latest is None:
            raise FileNotFoundError("No profiler runs exist")
        return latest
    path = run_path(root, run_id)
    if path.exists():
        return path
    direct = root / PROFILER_DIR / "runs" / f"{run_id}.json"
    if direct.exists():
        return direct
    raise FileNotFoundError(f"Run not found: {run_id}")


def latest_run_path(root: Path) -> Path | None:
    runs_dir = root / PROFILER_DIR / "runs"
    runs = sorted(runs_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)
    return runs[-1] if runs else None


def recent_run_paths(root: Path, count: int) -> list[Path]:
    runs_dir = root / PROFILER_DIR / "runs"
    runs = sorted(runs_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return runs[:count]


def set_active_run(root: Path, run_id: str) -> None:
    (root / PROFILER_DIR / "active-run").write_text(run_id, encoding="utf-8")


def get_active_run_id(root: Path) -> str:
    path = root / PROFILER_DIR / "active-run"
    if not path.exists():
        raise FileNotFoundError("No active run. Start one with `agent-profiler start --case <id>`.")
    return path.read_text(encoding="utf-8").strip()


def clear_active_run(root: Path) -> None:
    path = root / PROFILER_DIR / "active-run"
    if path.exists():
        path.unlink()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
