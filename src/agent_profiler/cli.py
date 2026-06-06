from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from agent_profiler.command_runner import run_wrapped_command
from agent_profiler.config import load_case, load_config
from agent_profiler.git_inspector import (
    analyze_changed_files,
    diff,
    dirty_status,
    ensure_git_repo,
    snapshot,
)
from agent_profiler.models import RunMetadata
from agent_profiler.reports.comparison import write_comparison_report
from agent_profiler.reports.markdown import write_markdown_report
from agent_profiler.rules import analyze_run
from agent_profiler.scoring import score_run
from agent_profiler.storage import (
    clear_active_run,
    ensure_layout,
    get_active_run_id,
    load_run,
    save_run,
    set_active_run,
    write_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"agent-profiler: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-profiler")
    subcommands = parser.add_subparsers(required=True)

    init_parser = subcommands.add_parser("init")
    init_parser.set_defaults(func=cmd_init)

    start_parser = subcommands.add_parser("start")
    start_parser.add_argument("--case", required=True, dest="case_id")
    start_parser.set_defaults(func=cmd_start)

    run_parser = subcommands.add_parser("run")
    run_parser.add_argument("command", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=cmd_run)

    finish_parser = subcommands.add_parser("finish")
    finish_parser.set_defaults(func=cmd_finish)

    report_parser = subcommands.add_parser("report")
    report_parser.add_argument("--run", default="latest", dest="run_id")
    report_parser.set_defaults(func=cmd_report)

    compare_parser = subcommands.add_parser("compare")
    compare_parser.add_argument("--last", type=int, default=10, dest="last")
    compare_parser.set_defaults(func=cmd_compare)
    return parser


def cmd_init(args: argparse.Namespace) -> int:
    root = Path.cwd()
    ensure_layout(root)
    print("Created .agent-profiler folder structure and default config.")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    root = Path.cwd()
    ensure_layout(root)
    ensure_git_repo(root)
    case, case_path = load_case(root, args.case_id)
    started_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    run_id = f"{started_at.replace(':', '-')}_{args.case_id}"
    baseline = snapshot(root)
    snapshot_path = root / ".agent-profiler" / "snapshots" / f"{run_id}_before.json"
    write_json(snapshot_path, baseline)
    run = RunMetadata(
        run_id=run_id,
        case_id=args.case_id,
        agent=case.get("agent"),
        repo_path=str(root),
        started_at=started_at,
        branch_before=baseline.get("branch"),
        commit_before=baseline.get("commit"),
        baseline_snapshot_path=snapshot_path.relative_to(root).as_posix(),
        case_path=case_path.relative_to(root).as_posix(),
        case=case,
    )
    save_run(root, run)
    set_active_run(root, run.path_safe_id)
    status = dirty_status(root)
    if status:
        print("Warning: workspace is dirty at run start.")
    print(f"Started run: {run.run_id}")
    print("")
    print("Task prompt:")
    print(case.get("task_prompt", "No task_prompt configured."))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if not args.command:
        raise ValueError("Missing command to run")
    root = Path.cwd()
    ensure_layout(root)
    run = load_run(root, get_active_run_id(root))
    command = " ".join(args.command)
    record = run_wrapped_command(root, run.path_safe_id, command, len(run.commands) + 1)
    run.commands.append(record)
    save_run(root, run)
    print(f"Command exited {record.exit_code}; output captured at {record.output_path}")
    return record.exit_code


def cmd_finish(args: argparse.Namespace) -> int:
    root = Path.cwd()
    ensure_layout(root)
    config = load_config(root)
    run = load_run(root, get_active_run_id(root))
    final = snapshot(root)
    final_snapshot_path = root / ".agent-profiler" / "snapshots" / f"{run.path_safe_id}_after.json"
    write_json(final_snapshot_path, final)

    forbidden = _forbidden_patterns(run, config)
    required_reports = [
        str(path) for path in run.case.get("validation", {}).get("required_reports", [])
    ]
    run.finished_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    run.branch_after = final.get("branch")
    run.commit_after = final.get("commit")
    run.final_snapshot_path = final_snapshot_path.relative_to(root).as_posix()
    run.changed_files = analyze_changed_files(root, forbidden)
    run.diff = diff(root)
    run.reports = [path for path in required_reports if (root / path).exists()]
    run.findings = analyze_run(root, run, config)
    run.score, run.verdict = score_run(run)
    save_run(root, run)
    clear_active_run(root)
    print(f"Finished run: {run.run_id}")
    print(f"Findings: {len(run.findings)}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    root = Path.cwd()
    ensure_layout(root)
    run = load_run(root, args.run_id)
    path = write_markdown_report(root, run)
    print(f"Wrote report: {path.relative_to(root).as_posix()}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    if args.last < 1:
        raise ValueError("--last must be at least 1")
    root = Path.cwd()
    ensure_layout(root)
    path = write_comparison_report(root, args.last)
    print(f"Wrote comparison report: {path.relative_to(root).as_posix()}")
    return 0


def _forbidden_patterns(run: RunMetadata, config: dict[str, object]) -> list[str]:
    config_rules = config.get("rules", {})
    config_forbidden: list[str] = []
    if isinstance(config_rules, dict):
        configured = config_rules.get("forbidden_paths", [])
        if isinstance(configured, list):
            config_forbidden = [str(item) for item in configured]
    expected = run.case.get("expected", {})
    case_forbidden = expected.get("forbidden_paths", []) if isinstance(expected, dict) else []
    return [*config_forbidden, *[str(item) for item in case_forbidden]]


if __name__ == "__main__":
    raise SystemExit(main())
