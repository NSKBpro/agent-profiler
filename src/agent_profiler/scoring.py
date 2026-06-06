from __future__ import annotations

from agent_profiler.models import RunMetadata


def score_run(run: RunMetadata) -> tuple[dict[str, int], str]:
    score = {
        "correctness": 40,
        "instruction_compliance": 20,
        "scope_control": 15,
        "validation_quality": 10,
        "efficiency": 10,
        "report_quality": 5,
    }
    for finding in run.findings:
        if finding.id == "missing_report":
            score["instruction_compliance"] = max(0, score["instruction_compliance"] - 10)
            score["report_quality"] = 0
        elif finding.id == "forbidden_file_changed":
            score["scope_control"] = max(0, score["scope_control"] - 15)
            score["instruction_compliance"] = max(0, score["instruction_compliance"] - 5)
        elif finding.id == "repeated_failure":
            score["efficiency"] = max(0, score["efficiency"] - 6)
            score["validation_quality"] = max(0, score["validation_quality"] - 2)
        elif finding.id in {
            "large_command_output",
            "formatting_heavy_diff",
            "mechanical_repeated_edit",
            "full_test_suite_overuse",
        }:
            score["efficiency"] = max(0, score["efficiency"] - 2)
        elif finding.id == "broad_file_spread":
            score["scope_control"] = max(0, score["scope_control"] - 4)
        elif finding.id == "suspicious_near_duplicate_filename":
            score["scope_control"] = max(0, score["scope_control"] - 3)
        elif finding.id == "lock_file_changed_unexpectedly":
            score["scope_control"] = max(0, score["scope_control"] - 6)
            score["instruction_compliance"] = max(0, score["instruction_compliance"] - 4)
        elif finding.id == "missing_tests":
            score["validation_quality"] = max(0, score["validation_quality"] - 4)
        elif finding.id == "generated_file_changed_manually":
            score["scope_control"] = max(0, score["scope_control"] - 3)
        elif finding.id == "low_reviewability":
            score["report_quality"] = max(0, score["report_quality"] - 2)
    if not run.commands:
        score["validation_quality"] = 0
    if any(command.exit_code != 0 for command in run.commands):
        score["correctness"] = max(0, score["correctness"] - 10)

    total = sum(score.values())
    if any(finding.severity == "high" for finding in run.findings):
        verdict = "NEEDS_HUMAN_REVIEW"
    elif run.findings:
        verdict = "PASS_WITH_WARNINGS"
    elif total >= 80:
        verdict = "PASS"
    else:
        verdict = "PASS_WITH_WARNINGS"
    return score, verdict
