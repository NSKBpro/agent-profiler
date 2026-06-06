from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from agent_profiler.models import ChangedFile


def run_git(root: Path, args: list[str], *, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def ensure_git_repo(root: Path) -> None:
    run_git(root, ["rev-parse", "--show-toplevel"])


def snapshot(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["ls-files"]).splitlines()
    return {
        "branch": run_git(root, ["branch", "--show-current"], check=False),
        "commit": run_git(root, ["rev-parse", "HEAD"], check=False),
        "status": run_git(root, ["status", "--porcelain"], check=False),
        "tracked_file_hashes": _tracked_file_hashes(root, tracked),
        "report_files": _matching_files(
            root, [".agent-profiler/reports/*.md", ".copilot/reports/**/*.md"]
        ),
        "instruction_file_hashes": _instruction_file_hashes(root),
    }


def dirty_status(root: Path) -> str:
    return run_git(root, ["status", "--porcelain"], check=False)


def diff(root: Path) -> str:
    return run_git(root, ["diff", "HEAD"], check=False)


def analyze_changed_files(root: Path, forbidden_patterns: list[str]) -> list[ChangedFile]:
    numstat = _numstat(root)
    statuses = _status_map(root)
    paths = sorted(set(numstat) | set(statuses))
    return [
        ChangedFile(
            path=path,
            status=statuses.get(path, "modified"),
            lines_added=numstat.get(path, (0, 0))[0],
            lines_removed=numstat.get(path, (0, 0))[1],
            is_test_file=_is_test_file(path),
            is_generated_file=_is_generated_file(path),
            is_forbidden=_matches_any(path, forbidden_patterns),
        )
        for path in paths
    ]


def _tracked_file_hashes(root: Path, tracked: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in tracked:
        path = root / relative
        if path.is_file():
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _instruction_file_hashes(root: Path) -> dict[str, str]:
    files = [root / "AGENTS.md", root / ".github" / "copilot-instructions.md"]
    hashes: dict[str, str] = {}
    for path in files:
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    for path in (root / ".github").glob("instructions/**/*.instructions.md"):
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return hashes


def _matching_files(root: Path, patterns: list[str]) -> list[str]:
    found: set[str] = set()
    for pattern in patterns:
        found.update(
            path.relative_to(root).as_posix() for path in root.glob(pattern) if path.is_file()
        )
    return sorted(found)


def _numstat(root: Path) -> dict[str, tuple[int, int]]:
    output = run_git(root, ["diff", "--numstat", "HEAD"], check=False)
    changes: dict[str, tuple[int, int]] = {}
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            added = 0 if parts[0] == "-" else int(parts[0])
            removed = 0 if parts[1] == "-" else int(parts[1])
            changes[parts[2]] = (added, removed)
    return changes


def _status_map(root: Path) -> dict[str, str]:
    output = run_git(root, ["status", "--porcelain"], check=False)
    statuses: dict[str, str] = {}
    status_names = {
        "A": "added",
        "M": "modified",
        "D": "deleted",
        "R": "renamed",
        "C": "copied",
        "?": "untracked",
    }
    for line in output.splitlines():
        if len(line) < 4:
            continue
        code = line[:2].strip() or line[1].strip()
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        statuses[path] = status_names.get(code[0], "modified")
    return statuses


def _matches_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(Path(normalized).match(pattern) for pattern in patterns)


def _is_test_file(path: str) -> bool:
    parts = Path(path).parts
    return "tests" in parts or Path(path).name.startswith("test_")


def _is_generated_file(path: str) -> bool:
    lowered = path.lower()
    return any(token in lowered for token in ("generated", ".min.", "lock"))
