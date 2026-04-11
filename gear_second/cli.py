"""
cli.py — Gear Second Phase 1 CLI entry point.
Commands: status, brief (+ bare invocation shows status)
"""
import argparse
import sys
from typing import Optional

from gear_second import __version__
from gear_second.context_loader import load_context
from gear_second.governance import (
    get_write_authority_summary,
    get_missing_governance_note,
    classify_path,
)
from gear_second.models import RepoContext
from gear_second import ui


def cmd_status(ctx: RepoContext) -> None:
    """gear-second status — repo, branch, venture, governance, write authority."""
    ui.header()
    ui.section("Session Context")
    ui.row("CWD", ctx.cwd)
    ui.row("Repo root", ctx.repo_root, warn=not ctx.is_git_repo)
    ui.row("Git repo", "yes" if ctx.is_git_repo else "no", warn=not ctx.is_git_repo)
    ui.row("Branch", ctx.branch, warn=ctx.branch in (None, "HEAD"))
    ui.row("Venture", ctx.venture, warn=ctx.venture is None)
    ui.row("Task ID", ctx.task_id)
    ui.row("Mode", ctx.mode)
    ui.row("Backend model", ctx.backend_model)

    ui.section("Governance")
    loaded = ctx.governance.sources_loaded
    if loaded:
        for src in loaded:
            ui.ok(src)
    else:
        ui.warn("No governance files loaded.")

    missing_note = get_missing_governance_note(ctx)
    if ctx.governance.missing:
        ui.warn(missing_note)
    else:
        ui.ok(missing_note)

    ui.section("Write Authority")
    print()
    for line in get_write_authority_summary(ctx).splitlines():
        print(f"  {line}")

    ui.section("Governance Conflicts")
    if ctx.governance.missing:
        ui.warn(f"{len(ctx.governance.missing)} governance file(s) missing — conservative defaults apply.")
    else:
        ui.ok("No conflicts detected.")

    ui.divider()


def cmd_brief(ctx: RepoContext) -> None:
    """gear-second brief — concise project/task summary with governance notes."""
    ui.header()
    ui.section("Brief")

    venture_str = ctx.venture or "Unknown — could not detect from path"
    branch_str = ctx.branch or "Not in a git repo"
    repo_str = ctx.repo_root or ctx.cwd

    print(f"""
  Venture:   {venture_str}
  Repo:      {repo_str}
  Branch:    {branch_str}
  Task ID:   {ctx.task_id or '—'}
  Mode:      {ctx.mode}
""")

    if ctx.recent_changes:
        ui.section("Recent Commits")
        for line in ctx.recent_changes[:5]:
            print(f"    {line}")

    ui.section("Governance Summary")
    sources = ctx.governance.sources_loaded
    if sources:
        print(f"  {len(sources)} governance file(s) loaded:")
        for s in sources:
            print(f"    · {s}")
    else:
        ui.warn("No governance files found. Conservative defaults apply.")

    if ctx.governance.missing:
        ui.warn(f"Missing: {', '.join(ctx.governance.missing)}")

    ui.section("Authority Boundaries")
    print()
    for line in get_write_authority_summary(ctx).splitlines():
        print(f"  {line}")

    if ctx.governance.open_tasks:
        ui.section("Open Tasks (brain-level)")
        lines = ctx.governance.open_tasks.splitlines()
        # Show only active task lines
        for line in lines:
            if "| IN_PROGRESS |" in line or "| PENDING |" in line or "| BLOCKED |" in line:
                print(f"  {line.strip()}")

    ui.divider()
    print(f"\n  {ui.DIM}Gear Second v{__version__} · Phase 1{ui.RESET}\n")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gear-second",
        description="Gear Second — P51 Brain governed failover mode",
    )
    parser.add_argument("command", nargs="?", default="status",
                        choices=["status", "brief", "start"],
                        help="Command to run (default: status)")
    parser.add_argument("--venture", "-v", default=None, help="Override venture name")
    parser.add_argument("--task", "-t", default=None, help="Task ID to load")
    parser.add_argument("--mode", "-m", default="auto",
                        choices=["auto", "claude-ollama", "local"],
                        help="Operating mode (default: auto)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args(argv)

    ctx = load_context(
        venture=args.venture,
        task_id=args.task,
        mode=args.mode,
    )

    if args.command in ("status", "start", None):
        cmd_status(ctx)
    elif args.command == "brief":
        cmd_brief(ctx)

    return 0


if __name__ == "__main__":
    sys.exit(main())
