from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Severity = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]


@dataclass(slots=True)
class Finding:
    id: str
    severity: Severity
    confidence: Confidence
    title: str
    evidence: list[str]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        return cls(
            id=str(data["id"]),
            severity=data["severity"],
            confidence=data["confidence"],
            title=str(data["title"]),
            evidence=[str(item) for item in data.get("evidence", [])],
            recommendation=str(data["recommendation"]),
        )


@dataclass(slots=True)
class CommandRecord:
    command: str
    working_directory: str
    started_at: str
    ended_at: str
    duration_seconds: float
    exit_code: int
    stdout_lines: int
    stderr_lines: int
    stdout_bytes: int
    stderr_bytes: int
    output_path: str
    failure_signature: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandRecord:
        return cls(
            command=str(data["command"]),
            working_directory=str(data["working_directory"]),
            started_at=str(data["started_at"]),
            ended_at=str(data["ended_at"]),
            duration_seconds=float(data["duration_seconds"]),
            exit_code=int(data["exit_code"]),
            stdout_lines=int(data["stdout_lines"]),
            stderr_lines=int(data["stderr_lines"]),
            stdout_bytes=int(data["stdout_bytes"]),
            stderr_bytes=int(data["stderr_bytes"]),
            output_path=str(data["output_path"]),
            failure_signature=data.get("failure_signature"),
        )


@dataclass(slots=True)
class ChangedFile:
    path: str
    status: str
    lines_added: int = 0
    lines_removed: int = 0
    is_test_file: bool = False
    is_generated_file: bool = False
    is_forbidden: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangedFile:
        return cls(
            path=str(data["path"]),
            status=str(data["status"]),
            lines_added=int(data.get("lines_added", 0)),
            lines_removed=int(data.get("lines_removed", 0)),
            is_test_file=bool(data.get("is_test_file", False)),
            is_generated_file=bool(data.get("is_generated_file", False)),
            is_forbidden=bool(data.get("is_forbidden", False)),
        )


@dataclass(slots=True)
class UsageMetadata:
    provider: str
    model: str
    agent: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    premium_requests: int | None = None
    estimated_cost: float | None = None
    duration_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageMetadata:
        return cls(
            provider=str(data["provider"]),
            model=str(data["model"]),
            agent=str(data["agent"]) if data.get("agent") is not None else None,
            input_tokens=_optional_int(data.get("input_tokens")),
            output_tokens=_optional_int(data.get("output_tokens")),
            cached_tokens=_optional_int(data.get("cached_tokens")),
            premium_requests=_optional_int(data.get("premium_requests")),
            estimated_cost=_optional_float(data.get("estimated_cost")),
            duration_seconds=_optional_float(data.get("duration_seconds")),
        )


@dataclass(slots=True)
class RunMetadata:
    run_id: str
    case_id: str | None
    agent: str | None
    repo_path: str
    started_at: str
    finished_at: str | None = None
    branch_before: str | None = None
    commit_before: str | None = None
    branch_after: str | None = None
    commit_after: str | None = None
    baseline_snapshot_path: str | None = None
    final_snapshot_path: str | None = None
    case_path: str | None = None
    case: dict[str, Any] = field(default_factory=dict)
    commands: list[CommandRecord] = field(default_factory=list)
    changed_files: list[ChangedFile] = field(default_factory=list)
    diff: str = ""
    usage: UsageMetadata | None = None
    usage_path: str | None = None
    reports: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    score: dict[str, int] = field(default_factory=dict)
    verdict: str = "INVALID_RUN"

    @property
    def path_safe_id(self) -> str:
        return self.run_id.replace(":", "-")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["commands"] = [command.to_dict() for command in self.commands]
        data["changed_files"] = [changed_file.to_dict() for changed_file in self.changed_files]
        data["findings"] = [finding.to_dict() for finding in self.findings]
        data["usage"] = self.usage.to_dict() if self.usage else None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunMetadata:
        return cls(
            run_id=str(data["run_id"]),
            case_id=data.get("case_id"),
            agent=data.get("agent"),
            repo_path=str(data["repo_path"]),
            started_at=str(data["started_at"]),
            finished_at=data.get("finished_at"),
            branch_before=data.get("branch_before"),
            commit_before=data.get("commit_before"),
            branch_after=data.get("branch_after"),
            commit_after=data.get("commit_after"),
            baseline_snapshot_path=data.get("baseline_snapshot_path"),
            final_snapshot_path=data.get("final_snapshot_path"),
            case_path=data.get("case_path"),
            case=dict(data.get("case", {})),
            commands=[CommandRecord.from_dict(item) for item in data.get("commands", [])],
            changed_files=[ChangedFile.from_dict(item) for item in data.get("changed_files", [])],
            diff=str(data.get("diff", "")),
            usage=UsageMetadata.from_dict(data["usage"]) if data.get("usage") else None,
            usage_path=data.get("usage_path"),
            reports=[str(item) for item in data.get("reports", [])],
            findings=[Finding.from_dict(item) for item in data.get("findings", [])],
            score={str(key): int(value) for key, value in data.get("score", {}).items()},
            verdict=str(data.get("verdict", "INVALID_RUN")),
        )


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def as_repo_relative(repo_path: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_path.resolve()).as_posix()
