from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from agent_profiler.config import load_config, read_yaml, write_yaml
from agent_profiler.models import UsageMetadata
from agent_profiler.rules import analyze_run
from agent_profiler.scoring import score_run
from agent_profiler.storage import load_run, save_run


def attach_usage_file(root: Path, run_id: str, source: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Usage file not found: {source}")
    run = load_run(root, run_id)
    usage = load_usage(source)
    target = root / ".agent-profiler" / "usage" / f"{run.path_safe_id}.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    run.usage = usage
    run.usage_path = target.relative_to(root).as_posix()
    run.findings = analyze_run(root, run, load_config(root))
    run.score, run.verdict = score_run(run)
    save_run(root, run)
    return target


def load_usage(path: Path) -> UsageMetadata:
    data = read_yaml(path)
    if not data.get("provider"):
        raise ValueError("Usage file must include provider")
    if not data.get("model"):
        raise ValueError("Usage file must include model")
    return UsageMetadata.from_dict(_usage_fields(data))


def write_usage(path: Path, usage: UsageMetadata) -> None:
    write_yaml(path, usage.to_dict())


def _usage_fields(data: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "provider",
        "agent",
        "model",
        "input_tokens",
        "output_tokens",
        "cached_tokens",
        "premium_requests",
        "estimated_cost",
        "duration_seconds",
    }
    return {key: value for key, value in data.items() if key in allowed}
