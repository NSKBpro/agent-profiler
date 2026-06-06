from __future__ import annotations

from agent_profiler.models import Finding

_SUGGESTIONS_BY_FINDING_ID = {
    "changed_file_outside_allowed_paths": "Tighten allowed paths in the prompt.",
    "broad_file_spread": "Split broad changes into smaller agent tasks.",
    "missing_required_validation_command": "Add required validation commands to the prompt.",
    "source_changed_without_pytest": "Require pytest validation for source changes.",
    "docs_only_overvalidation": "Use targeted validation for docs-only changes.",
    "expensive_invalid_run": "Add stop conditions and preflight checks to reduce wasted spend.",
    "high_cost_low_change": "Use deterministic tools or smaller context for tiny changes.",
    "high_output_token_ratio": "Ask the agent for concise output and compact reports.",
    "expensive_docs_only_run": "Use cheaper deterministic checks for docs-only changes.",
    "missing_tests": "Ask the agent to add or justify focused tests.",
    "forbidden_file_changed": "Reinforce forbidden paths and safety constraints.",
    "low_reviewability": "Split broad changes into smaller agent tasks.",
}


def optimization_suggestions(findings: list[Finding]) -> list[str]:
    suggestions: list[str] = []
    for finding in findings:
        suggestion = _SUGGESTIONS_BY_FINDING_ID.get(finding.id)
        if suggestion and suggestion not in suggestions:
            suggestions.append(suggestion)
    return suggestions
