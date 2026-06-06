from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from agent_profiler.models import ChangedFile, Finding, RunMetadata


def analyze_run(root: Path, run: RunMetadata, config: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_missing_required_reports(root, run))
    findings.extend(_changed_files_outside_allowed_paths(run))
    findings.extend(_missing_required_validation_commands(run))
    findings.extend(_source_changed_without_pytest(run))
    findings.extend(_docs_only_overvalidation(run))
    findings.extend(_usage_cost_findings(run))
    findings.extend(_forbidden_file_changes(run))
    findings.extend(_repeated_command_failures(run, config))
    findings.extend(_large_command_outputs(run, config))
    findings.extend(_formatting_heavy_diff(run, config))
    findings.extend(_mechanical_repeated_edit(run, config))
    findings.extend(_broad_file_spread(run, config))
    findings.extend(_suspicious_near_duplicate_filenames(root, run))
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


def _changed_files_outside_allowed_paths(run: RunMetadata) -> list[Finding]:
    allowed = _configured_list(run.case.get("expected", {}), "allowed_paths")
    if not allowed:
        return []
    outside = [
        changed_file.path
        for changed_file in run.changed_files
        if not _matches_any_pattern(changed_file.path, allowed)
    ]
    if not outside:
        return []
    return [
        Finding(
            id="changed_file_outside_allowed_paths",
            severity="high",
            confidence="high",
            title="Changed file outside allowed paths",
            evidence=[f"Outside allowed paths: {path}" for path in outside],
            recommendation=(
                "Tighten allowed paths in the task prompt or require explicit justification for "
                "out-of-scope file changes."
            ),
        )
    ]


def _missing_required_validation_commands(run: RunMetadata) -> list[Finding]:
    required = _configured_list(run.case.get("validation", {}), "required_commands")
    if not required:
        return []
    captured = {_normalize_command(command.command) for command in run.commands}
    missing = [command for command in required if _normalize_command(command) not in captured]
    if not missing:
        return []
    return [
        Finding(
            id="missing_required_validation_command",
            severity="high",
            confidence="high",
            title="Required validation command was not captured",
            evidence=[f"Missing required command: {command}" for command in missing],
            recommendation=(
                "Add required validation commands to the agent workflow and run them through "
                "`agent-profiler run`."
            ),
        )
    ]


def _source_changed_without_pytest(run: RunMetadata) -> list[Finding]:
    source_changes = [
        changed_file.path
        for changed_file in run.changed_files
        if changed_file.path.startswith("src/")
    ]
    if not source_changes or _pytest_was_captured(run):
        return []
    return [
        Finding(
            id="source_changed_without_pytest",
            severity="medium",
            confidence="high",
            title="Source changed without captured pytest validation",
            evidence=[f"Source files changed: {', '.join(source_changes[:5])}"],
            recommendation=(
                "Run `python -m pytest` or a focused pytest target through the profiler."
            ),
        )
    ]


def _docs_only_overvalidation(run: RunMetadata) -> list[Finding]:
    if not run.changed_files or not all(
        _is_docs_only_path(item.path) for item in run.changed_files
    ):
        return []
    full_pytest_commands = [
        command.command for command in run.commands if _is_full_test_suite(command.command)
    ]
    if not full_pytest_commands:
        return []
    return [
        Finding(
            id="docs_only_overvalidation",
            severity="low",
            confidence="high",
            title="Docs-only change used full pytest validation",
            evidence=[
                f"Full pytest command captured: {command}" for command in full_pytest_commands
            ],
            recommendation=(
                "Use targeted validation for docs-only changes, such as Markdown checks or a "
                "lightweight smoke command."
            ),
        )
    ]


def _usage_cost_findings(run: RunMetadata) -> list[Finding]:
    if run.usage is None:
        return []
    findings: list[Finding] = []
    cost = run.usage.estimated_cost
    if cost is not None and cost >= 1.0 and run.verdict == "INVALID_RUN":
        findings.append(
            Finding(
                id="expensive_invalid_run",
                severity="high",
                confidence="high",
                title="Expensive invalid run",
                evidence=[f"Run verdict is INVALID_RUN with estimated cost {cost:.2f}"],
                recommendation=(
                    "Stop invalid runs earlier and add preflight checks before agent work."
                ),
            )
        )
    changed_lines = sum(item.lines_added + item.lines_removed for item in run.changed_files)
    if cost is not None and cost >= 0.5 and len(run.changed_files) <= 2 and changed_lines <= 20:
        findings.append(
            Finding(
                id="high_cost_low_change",
                severity="medium",
                confidence="medium",
                title="High cost for a small change",
                evidence=[
                    f"Estimated cost {cost:.2f} for {len(run.changed_files)} files and "
                    f"{changed_lines} changed lines"
                ],
                recommendation=(
                    "Use smaller prompts, scoped context, or deterministic tools for tiny changes."
                ),
            )
        )
    if (
        run.usage.input_tokens
        and run.usage.output_tokens
        and run.usage.output_tokens / run.usage.input_tokens >= 1.0
    ):
        findings.append(
            Finding(
                id="high_output_token_ratio",
                severity="medium",
                confidence="high",
                title="High output token ratio",
                evidence=[
                    (
                        f"Output tokens {run.usage.output_tokens} vs input tokens "
                        f"{run.usage.input_tokens}"
                    )
                ],
                recommendation=(
                    "Ask for concise reports and avoid copying large generated output back to "
                    "the agent."
                ),
            )
        )
    if (
        cost is not None
        and cost >= 0.25
        and run.changed_files
        and all(_is_docs_only_path(item.path) for item in run.changed_files)
    ):
        findings.append(
            Finding(
                id="expensive_docs_only_run",
                severity="medium",
                confidence="high",
                title="Expensive docs-only run",
                evidence=[f"Estimated cost {cost:.2f} for docs-only changes"],
                recommendation=(
                    "Use cheaper deterministic checks or manual edits for docs-only changes."
                ),
            )
        )
    return findings


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


def _suspicious_near_duplicate_filenames(root: Path, run: RunMetadata) -> list[Finding]:
    common_names = {
        "README.md",
        "LICENSE",
        "AGENTS.md",
        "pyproject.toml",
        "package.json",
    }
    suspicious: list[str] = []
    for changed_file in run.changed_files:
        changed_path = PurePosixPath(changed_file.path)
        changed_name = changed_path.name
        for common_name in common_names:
            if changed_name.lower() == common_name.lower():
                continue
            if changed_path.suffix.lower() != PurePosixPath(common_name).suffix.lower():
                continue
            existing_common = root / changed_path.parent / common_name
            if not existing_common.exists():
                continue
            if _edit_distance(changed_name.lower(), common_name.lower()) <= 2:
                suspicious.append(f"{changed_file.path} is similar to {common_name}")

    if not suspicious:
        return []
    return [
        Finding(
            id="suspicious_near_duplicate_filename",
            severity="medium",
            confidence="high",
            title="Suspicious near-duplicate filename changed",
            evidence=suspicious,
            recommendation=(
                "Review likely filename typo artifacts and remove or rename accidental duplicate "
                "files."
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


def _configured_list(section: Any, key: str) -> list[str]:
    if not isinstance(section, dict):
        return []
    value = section.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _matches_any_pattern(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(PurePosixPath(normalized).match(pattern) for pattern in patterns)


def _normalize_command(command: str) -> str:
    return " ".join(command.split())


def _pytest_was_captured(run: RunMetadata) -> bool:
    return any("pytest" in _normalize_command(command.command).lower() for command in run.commands)


def _is_docs_only_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = PurePosixPath(normalized).name.lower()
    return normalized.startswith("docs/") or name in {"readme.md", "readme"}


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


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            substitution_cost = 0 if left_char == right_char else 1
            current.append(
                min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]
