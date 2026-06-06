from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from agent_profiler.models import RunMetadata
from agent_profiler.reports.suggestions import optimization_suggestions
from agent_profiler.storage import load_run, recent_run_paths


def write_comparison_report(root: Path, last: int, valid_only: bool = False) -> Path:
    runs = [load_run(root, path.stem) for path in recent_run_paths(root, last)]
    excluded_invalid_runs = 0
    if valid_only:
        before = len(runs)
        runs = [run for run in runs if run.verdict != "INVALID_RUN"]
        excluded_invalid_runs = before - len(runs)
    if not runs:
        raise FileNotFoundError(
            "No profiler runs exist" if not valid_only else "No valid profiler runs exist"
        )
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "-")
    path = root / ".agent-profiler" / "reports" / f"comparison-{timestamp}-last-{len(runs)}.md"
    path.write_text(render_comparison_report(runs, excluded_invalid_runs), encoding="utf-8")
    return path


def render_comparison_report(runs: list[RunMetadata], excluded_invalid_runs: int = 0) -> str:
    verdict_counts = Counter(run.verdict for run in runs)
    finding_counts = Counter(finding.id for run in runs for finding in run.findings)
    title_by_id = {finding.id: finding.title for run in runs for finding in run.findings}
    recommendation_counts = Counter(
        finding.recommendation for run in runs for finding in run.findings
    )
    suggestion_counts = Counter(
        suggestion for run in runs for suggestion in optimization_suggestions(run.findings)
    )
    cost_recommendation_counts = Counter(
        finding.recommendation
        for run in runs
        for finding in run.findings
        if finding.id in _COST_FINDING_IDS
    )
    agents = Counter(run.agent or "unknown" for run in runs)
    cases = Counter(run.case_id or "none" for run in runs)
    lines = [
        "# Agent Profiler Comparison Report",
        "",
        "## Summary",
        "",
        f"- Run count: {len(runs)}",
        f"- Average score: {_average_score(runs):.1f}/100",
        f"- Average cost per run: {_average_cost(runs):.4f}",
        f"- Average cost per valid run: {_average_cost(_valid_runs(runs)):.4f}",
        f"- Invalid-run estimated waste: {_invalid_run_waste(runs):.4f}",
    ]
    if excluded_invalid_runs:
        lines += ["", f"- Invalid runs excluded: {excluded_invalid_runs}", ""]
    lines += [
        "## Runs Compared",
        "",
        *[f"- {run.run_id} ({run.verdict})" for run in runs],
        "",
        "## Verdict Counts",
        "",
        *_counter_lines(verdict_counts),
        "",
        "## Most Common Findings",
        "",
        *_finding_lines(finding_counts, title_by_id),
        "",
        "## Repeated Bottlenecks",
        "",
        *_repeated_bottleneck_lines(finding_counts, title_by_id),
        "",
        "## Agents and Cases",
        "",
        "### Agents",
        "",
        *_counter_lines(agents),
        "",
        "### Cases",
        "",
        *_counter_lines(cases),
        "",
        "## Most Expensive Cases",
        "",
        *_money_counter_lines(_costs_by_case(runs)),
        "",
        "## Most Expensive Agents",
        "",
        *_money_counter_lines(_costs_by_agent(runs)),
        "",
        "## Recommendations",
        "",
        *_counter_lines(recommendation_counts),
        "",
        "## Most Common Optimization Suggestions",
        "",
        *_counter_lines(suggestion_counts),
        "",
        "## Cost-Related Recommendations",
        "",
        *_counter_lines(cost_recommendation_counts),
        "",
    ]
    return "\n".join(lines)


def _average_score(runs: list[RunMetadata]) -> float:
    totals = [sum(run.score.values()) for run in runs if run.score]
    if not totals:
        return 0.0
    return sum(totals) / len(totals)


_COST_FINDING_IDS = {
    "expensive_invalid_run",
    "high_cost_low_change",
    "high_output_token_ratio",
    "expensive_docs_only_run",
}


def _average_cost(runs: list[RunMetadata]) -> float:
    costs = [
        run.usage.estimated_cost
        for run in runs
        if run.usage and run.usage.estimated_cost is not None
    ]
    if not costs:
        return 0.0
    return sum(costs) / len(costs)


def _valid_runs(runs: list[RunMetadata]) -> list[RunMetadata]:
    return [run for run in runs if run.verdict != "INVALID_RUN"]


def _invalid_run_waste(runs: list[RunMetadata]) -> float:
    return sum(
        run.usage.estimated_cost or 0.0
        for run in runs
        if run.verdict == "INVALID_RUN" and run.usage is not None
    )


def _costs_by_case(runs: list[RunMetadata]) -> Counter[str]:
    costs: Counter[str] = Counter()
    for run in runs:
        if run.usage and run.usage.estimated_cost is not None:
            costs[run.case_id or "none"] += run.usage.estimated_cost
    return costs


def _costs_by_agent(runs: list[RunMetadata]) -> Counter[str]:
    costs: Counter[str] = Counter()
    for run in runs:
        if run.usage and run.usage.estimated_cost is not None:
            costs[run.agent or run.usage.agent or "unknown"] += run.usage.estimated_cost
    return costs


def _counter_lines(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["None."]
    return [f"- {name}: {count}" for name, count in counter.most_common()]


def _money_counter_lines(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["None."]
    return [f"- {name}: {amount:.4f}" for name, amount in counter.most_common()]


def _finding_lines(counter: Counter[str], title_by_id: dict[str, str]) -> list[str]:
    if not counter:
        return ["None."]
    return [
        f"- {finding_id}: {count} ({title_by_id.get(finding_id, finding_id)})"
        for finding_id, count in counter.most_common()
    ]


def _repeated_bottleneck_lines(counter: Counter[str], title_by_id: dict[str, str]) -> list[str]:
    repeated = Counter({finding_id: count for finding_id, count in counter.items() if count > 1})
    return _finding_lines(repeated, title_by_id)
