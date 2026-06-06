from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from agent_profiler.models import ChangedFile, Finding, RunMetadata


def analyze_run(root: Path, run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_missing_required_reports(root, run))
    findings.extend(_forbidden_file_changes(run))
    findings.extend(_repeated_command_failures(run, config))
    findings.extend(_large_command_outputs(run, config))
    findings.extend(_formatting_heavy_diff(run, config))
    findings.extend(_mechanical_repeated_edit(run, config))
    findings.extend(_broad_file_spread(run, config))
    findings.extend(_full_test_suite_overuse(run, config))
    findings.extend(_lock_file_changed_unexpectedly(run))
    findings.extend(_missing_tests(run))
    findings.extend(_generated_file_changed_manually(run))
    findings.extend(_low_reviewability(run, config))
    return findings


def _missing_required_reports(root: Path, run: RunMetadata) -> list[Finding]:
    required = run.case.get("validation", {}).get("required_reports", [])
    missing = [str(path) for path in required if not (root / str(path)).exists()]
    if not missing:
        return []
    return [
        Finding(
            id="missing_report",
            severity="high",
            confidence="high",
            title="Required report artifact is missing",
            evidence=[f"Missing required report: {path}" for path in missing],
            recommendation=(
                "Require the agent to create the expected Markdown report before finish."
            ),
        )
    ]


def _forbidden_file_changes(run: RunMetadata) -> list[Finding]:
    forbidden = [
        changed_file.path for changed_file in run.changed_files if changed_file.is_forbidden
    ]
    if not forbidden:
        return []
    return [
        Finding(
            id="forbidden_file_changed",
            severity="high",
            confidence="high",
            title="Forbidden file changed",
            evidence=[f"Forbidden path changed: {path}" for path in forbidden],
            recommendation="Reject the run or require human review for forbidden path changes.",
        )
    ]


def _repeated_command_failures(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    rule = config.get("rules", {}).get("repeated_failure", {})
    if not rule.get("enabled", True):
        return []
    threshold = int(rule.get("max_same_failure_count", 2))
    signatures = [
        command.failure_signature
        for command in run.commands
        if command.exit_code != 0 and command.failure_signature
    ]
    counts = Counter(signatures)
    repeated = {signature: count for signature, count in counts.items() if count >= threshold}
    if not repeated:
        return []
    evidence = [
        f"Failure signature repeated {count} times: {signature}"
        for signature, count in sorted(repeated.items())
    ]
    return [
        Finding(
            id="repeated_failure",
            severity="high",
            confidence="high",
            title="Repeated identical command failure",
            evidence=evidence,
            recommendation=(
                "Stop after repeated identical failures and ask for human input or change "
                "diagnostics."
            ),
        )
    ]


def _large_command_outputs(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    rule = config.get("rules", {}).get("large_command_output", {})
    if not rule.get("enabled", True):
        return []
    max_lines = int(rule.get("max_lines", 1000))
    oversized = [
        command
        for command in run.commands
        if command.stdout_lines + command.stderr_lines > max_lines
    ]
    if not oversized:
        return []
    return [
        Finding(
            id="large_command_output",
            severity="medium",
            confidence="high",
            title="Large command output captured",
            evidence=[
                f"`{command.command}` produced {command.stdout_lines + command.stderr_lines} lines"
                for command in oversized
            ],
            recommendation="Use focused commands, output summarization, or last-N-lines filtering.",
        )
    ]


def _formatting_heavy_diff(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    changed_lines = _changed_diff_lines(run.diff)
    if len(changed_lines) < 8:
        return []
    formatting_lines = [line for line in changed_lines if _looks_formatting_only(line)]
    threshold = float(
        config.get("rules", {}).get("formatting_heavy_diff", {}).get("threshold_percent", 70)
    )
    percent = round((len(formatting_lines) / len(changed_lines)) * 100)
    if percent < threshold:
        return []
    return [
        Finding(
            id="formatting_heavy_diff",
            severity="medium",
            confidence="medium",
            title="Formatting-heavy diff",
            evidence=[
                f"{percent}% of changed diff lines look formatting-only",
                (
                    f"{len(formatting_lines)} of {len(changed_lines)} changed lines matched "
                    "formatting patterns"
                ),
            ],
            recommendation=(
                "Run a formatter or linter fix command instead of spending agent effort on "
                "mechanical formatting."
            ),
        )
    ]


def _mechanical_repeated_edit(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    threshold = int(
        config.get("rules", {}).get("mechanical_repeated_edit", {}).get("min_repetitions", 3)
    )
    normalized = [_normalize_edit_line(line) for line in _changed_diff_lines(run.diff)]
    repeated = {
        line: count
        for line, count in Counter(line for line in normalized if line).items()
        if count >= threshold
    }
    if not repeated:
        return []
    evidence = [
        f"Repeated edit pattern {count} times: {line}" for line, count in sorted(repeated.items())
    ]
    return [
        Finding(
            id="mechanical_repeated_edit",
            severity="medium",
            confidence="medium",
            title="Mechanical repeated edit pattern",
            evidence=evidence,
            recommendation="Use a deterministic script or codemod for repeated edit patterns.",
        )
    ]


def _broad_file_spread(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    max_dirs = int(
        config.get("rules", {}).get("broad_file_spread", {}).get("max_top_level_dirs", 2)
    )
    top_level_dirs = sorted(
        {
            _top_level(changed_file.path)
            for changed_file in run.changed_files
            if not changed_file.path.startswith(".agent-profiler/")
        }
    )
    if len(top_level_dirs) <= max_dirs:
        return []
    return [
        Finding(
            id="broad_file_spread",
            severity="medium",
            confidence="medium",
            title="Changed files span many top-level areas",
            evidence=[f"Changed top-level areas: {', '.join(top_level_dirs)}"],
            recommendation=(
                "Add allowed paths, forbidden paths, or a planning checkpoint for broad changes."
            ),
        )
    ]


def _full_test_suite_overuse(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    threshold = int(
        config.get("rules", {}).get("full_test_suite_overuse", {}).get("min_repetitions", 2)
    )
    full_suite_commands = [
        command.command for command in run.commands if _is_full_test_suite(command.command)
    ]
    non_test_changes = [item for item in run.changed_files if not item.is_test_file]
    narrow_change = 0 < len(non_test_changes) <= 3
    if len(full_suite_commands) < threshold or not narrow_change:
        return []
    return [
        Finding(
            id="full_test_suite_overuse",
            severity="medium",
            confidence="medium",
            title="Full test suite run repeatedly for a narrow change",
            evidence=[f"Full-suite command repeated {len(full_suite_commands)} times"],
            recommendation=(
                "Run focused tests during repair loops and reserve the full suite for final "
                "validation."
            ),
        )
    ]


def _lock_file_changed_unexpectedly(run: RunMetadata) -> list[Finding]:
    changed_locks = [item.path for item in run.changed_files if _is_lock_file(item.path)]
    if not changed_locks or _task_mentions_dependencies(run):
        return []
    return [
        Finding(
            id="lock_file_changed_unexpectedly",
            severity="high",
            confidence="high",
            title="Dependency lock file changed unexpectedly",
            evidence=[f"Lock file changed: {path}" for path in changed_locks],
            recommendation="Require explicit approval for dependency or lock-file changes.",
        )
    ]


def _missing_tests(run: RunMetadata) -> list[Finding]:
    source_changes = [item.path for item in run.changed_files if _is_source_file(item)]
    test_changes = [item.path for item in run.changed_files if item.is_test_file]
    if not source_changes or test_changes:
        return []
    return [
        Finding(
            id="missing_tests",
            severity="medium",
            confidence="medium",
            title="Source changes were made without test changes",
            evidence=[f"Source files changed without test files: {', '.join(source_changes[:5])}"],
            recommendation=(
                "Add or update focused tests for source behavior changes, or document why tests "
                "were not needed."
            ),
        )
    ]


def _generated_file_changed_manually(run: RunMetadata) -> list[Finding]:
    generated = [item.path for item in run.changed_files if item.is_generated_file]
    if not generated or _generator_command_was_run(run):
        return []
    return [
        Finding(
            id="generated_file_changed_manually",
            severity="medium",
            confidence="medium",
            title="Generated file changed without generator evidence",
            evidence=[f"Generated-looking file changed: {path}" for path in generated],
            recommendation=(
                "Run the generator command and capture it through the profiler instead of manual "
                "generated-file edits."
            ),
        )
    ]


def _low_reviewability(run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    rule = config.get("rules", {}).get("low_reviewability", {})
    max_files = int(rule.get("max_changed_files", 10))
    max_lines = int(rule.get("max_changed_lines", 500))
    changed_lines = sum(item.lines_added + item.lines_removed for item in run.changed_files)
    reasons: list[str] = []
    if len(run.changed_files) > max_files:
        reasons.append(f"{len(run.changed_files)} files changed")
    if changed_lines > max_lines:
        reasons.append(f"{changed_lines} changed lines")
    if not reasons:
        return []
    return [
        Finding(
            id="low_reviewability",
            severity="medium",
            confidence="medium",
            title="Run output may be difficult to review",
            evidence=reasons,
            recommendation=(
                "Split the task, reduce diff size, and require concise implementation notes."
            ),
        )
    ]


def _changed_diff_lines(diff: str) -> list[str]:
    lines: list[str] = []
    for line in diff.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            lines.append(line[1:])
    return lines


def _looks_formatting_only(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped in {"{", "}", "(", ")", "[", "]", ",", "};", "];"}:
        return True
    if stripped.startswith(("import ", "from ")) and " as " not in stripped:
        return True
    punctuation = set("(){}[],:;,.")
    return bool(stripped) and all(character in punctuation for character in stripped)


def _normalize_edit_line(line: str) -> str:
    stripped = " ".join(line.strip().split())
    return stripped if len(stripped) >= 6 else ""


def _top_level(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if parts else path


def _is_full_test_suite(command: str) -> bool:
    normalized = " ".join(command.lower().split())
    return normalized in {"pytest", "python -m pytest"} or normalized.startswith(
        ("pytest --", "python -m pytest --")
    )


def _is_lock_file(path: str) -> bool:
    name = PurePosixPath(path).name.lower()
    return name in {
        "poetry.lock",
        "pdm.lock",
        "uv.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "cargo.lock",
        "gemfile.lock",
    }


def _task_mentions_dependencies(run: RunMetadata) -> bool:
    task_text = " ".join(str(run.case.get(key, "")) for key in ("title", "task_prompt")).lower()
    dependency_terms = ("dependency", "dependencies", "package", "install", "upgrade", "lock")
    return any(term in task_text for term in dependency_terms)


def _is_source_file(changed_file: ChangedFile) -> bool:
    if changed_file.is_test_file or changed_file.is_generated_file:
        return False
    suffix = PurePosixPath(changed_file.path).suffix.lower()
    return suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".cs"}


def _generator_command_was_run(run: RunMetadata) -> bool:
    generator_terms = ("generate", "codegen", "openapi", "protoc", "graphql-codegen")
    return any(
        any(term in command.command.lower() for term in generator_terms) for command in run.commands
    )
