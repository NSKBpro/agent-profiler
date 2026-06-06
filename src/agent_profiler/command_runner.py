from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from agent_profiler.models import CommandRecord


def run_wrapped_command(root: Path, run_id: str, command: str, index: int) -> CommandRecord:
    output_dir = root / ".agent-profiler" / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"command-{index:03d}.log"
    started = datetime.now(UTC)
    monotonic_start = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=root,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    ended = datetime.now(UTC)
    output_path.write_text(
        _format_output(command, completed.stdout, completed.stderr),
        encoding="utf-8",
    )
    return CommandRecord(
        command=command,
        working_directory=str(root),
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        duration_seconds=round(time.monotonic() - monotonic_start, 3),
        exit_code=completed.returncode,
        stdout_lines=len(completed.stdout.splitlines()),
        stderr_lines=len(completed.stderr.splitlines()),
        stdout_bytes=len(completed.stdout.encode()),
        stderr_bytes=len(completed.stderr.encode()),
        output_path=output_path.relative_to(root).as_posix(),
        failure_signature=_failure_signature(completed.stdout, completed.stderr)
        if completed.returncode != 0
        else None,
    )


def _format_output(command: str, stdout: str, stderr: str) -> str:
    return f"$ {command}\n\n[stdout]\n{stdout}\n\n[stderr]\n{stderr}"


def _failure_signature(stdout: str, stderr: str) -> str:
    combined = "\n".join([stdout, stderr])
    interesting = [
        line.strip()
        for line in combined.splitlines()
        if line.strip()
        and (
            "error" in line.lower()
            or "failed" in line.lower()
            or "assert" in line.lower()
            or "traceback" in line.lower()
        )
    ]
    if interesting:
        return interesting[-1][:240]
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    return (lines[-1] if lines else "command failed")[:240]
