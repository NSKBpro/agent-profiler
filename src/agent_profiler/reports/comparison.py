from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from agent_profiler.models import RunMetadata
from agent_profiler.storage import load_run, recent_run_paths


def write_comparison_report(root: Path, last: int) -> Path:
    runs = [load_run(root, path.stem) for path in recent_run_paths(root, last)]
    if not runs:
        raise FileNotFoundError("No profiler runs exist")
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "-")
    path = root / ".agent-profiler" / "reports" / f"comparison-{timestamp}-last-{len(runs)}.md"
    path.write_text(render_comparison_report(runs), encoding="utf-8")
    return path


def render_comparison_report(runs: list[RunMetadata]) -> str:
    verdict_counts = Counter(run.verdict for run in runs)
    finding_counts = Counter(finding.id for run in runs for finding in run.findings)
    title_by_id = {finding.id: finding.title for run in runs for finding in run.findings}
    recommendation_counts = Counter(
        finding.recommendation for run in runs for finding in run.findings
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
        "",
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
        "## Recommendations",
        "",
        *_counter_lines(recommendation_counts),
        "",
    ]
    return "\n".join(lines)


def _average_score(runs: list[RunMetadata]) -> float:
    totals = [sum(run.score.values()) for run in runs if run.score]
    if not totals:
        return 0.0
    return sum(totals) / len(totals)


def _counter_lines(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["None."]
    return [f"- {name}: {count}" for name, count in counter.most_common()]


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
