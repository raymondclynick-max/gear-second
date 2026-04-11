"""
cli.py — Gear Second Phases 1–5
Full CLI entry point with all subcommands.
"""
import argparse
import sys
import os
from pathlib import Path
from typing import Optional, List

from gear_second import __version__
from gear_second.context_loader import load_context
from gear_second.governance import (
    get_write_authority_summary,
    get_missing_governance_note,
    classify_path,
)
from gear_second.models import RepoContext
from gear_second import ui


# ── Phase 1 commands ──────────────────────────────────────────────────────────

def cmd_status(ctx: RepoContext) -> int:
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
    for src in ctx.governance.sources_loaded:
        ui.ok(src)
    if not ctx.governance.sources_loaded:
        ui.warn("No governance files loaded.")
    if ctx.governance.missing:
        ui.warn(get_missing_governance_note(ctx))
    else:
        ui.ok(get_missing_governance_note(ctx))

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
    return 0


def cmd_brief(ctx: RepoContext) -> int:
    ui.header()
    ui.section("Brief")
    print(f"""
  Venture:   {ctx.venture or 'Unknown — could not detect from path'}
  Repo:      {ctx.repo_root or ctx.cwd}
  Branch:    {ctx.branch or 'Not in a git repo'}
  Task ID:   {ctx.task_id or '—'}
  Mode:      {ctx.mode}
""")
    if ctx.recent_changes:
        ui.section("Recent Commits")
        for line in ctx.recent_changes[:5]:
            print(f"    {line}")

    ui.section("Governance Summary")
    if ctx.governance.sources_loaded:
        print(f"  {len(ctx.governance.sources_loaded)} governance file(s) loaded:")
        for s in ctx.governance.sources_loaded:
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
        for line in ctx.governance.open_tasks.splitlines():
            if "| IN_PROGRESS |" in line or "| PENDING |" in line or "| BLOCKED |" in line:
                print(f"  {line.strip()}")

    ui.divider()
    print(f"\n  {ui.DIM}Gear Second v{__version__} · Phase 1–5{ui.RESET}\n")
    return 0


# ── Phase 2 commands ──────────────────────────────────────────────────────────

def cmd_start(ctx: RepoContext, mode: str) -> int:
    from gear_second.backend import select_mode, mode_summary, mode_a_ready
    from gear_second.session import create_session
    from gear_second.logger import log_event
    from gear_second.ollama_adapter import launch_claude_via_ollama, OLLAMA_HOST

    ui.header()
    ui.section("Starting Session")

    resolved_mode, ollama_status = select_mode(mode)
    backend_model = ollama_status.model_name if mode_a_ready(ollama_status) else None

    ui.row("Mode resolved", resolved_mode)
    ui.row("Backend", mode_summary(resolved_mode, ollama_status))

    state = create_session(ctx, resolved_mode, backend_model)
    session_dir = Path(state.session_dir)
    log_event(session_dir, "session_start",
              f"venture={ctx.venture} repo={ctx.repo_root} branch={ctx.branch} mode={resolved_mode}")
    log_event(session_dir, "governance_loaded",
              f"{len(ctx.governance.sources_loaded)} files loaded")
    if ctx.governance.missing:
        log_event(session_dir, "governance_conflict",
                  f"missing: {', '.join(ctx.governance.missing)}")

    ui.ok(f"Session created: {state.session_id}")
    ui.ok(f"Session dir: {state.session_dir}")
    ui.ok(f"Context snapshot: {session_dir / 'context_snapshot.md'}")

    if ctx.governance.missing:
        for m in ctx.governance.missing:
            ui.warn(f"Missing governance: {m}")

    if resolved_mode == "claude-ollama":
        ui.section("Mode A — Launching Claude Code via Ollama")
        ui.row("Ollama host", OLLAMA_HOST)
        ui.row("Model", ollama_status.model_name)
        ui.row("ANTHROPIC_BASE_URL", f"{OLLAMA_HOST}/v1")
        print()
        log_event(session_dir, "mode_selected", "claude-ollama")
        try:
            exit_code = launch_claude_via_ollama(ctx.repo_root or ctx.cwd, OLLAMA_HOST)
            log_event(session_dir, "session_complete", f"claude exited with code {exit_code}")
            return exit_code
        except RuntimeError as e:
            ui.error(str(e))
            ui.warn("Falling back to Mode B (local wrapper).")
            log_event(session_dir, "session_error", f"Mode A launch failed: {e}")
            resolved_mode = "local"

    # Mode B — local wrapper
    ui.section("Mode B — Local Wrapper Active")
    ui.ok("Governance loaded. Type 'gear-second <command>' to continue working.")
    ui.ok(f"Session: {state.session_id}")
    print()
    print(f"  Available commands:")
    print(f"    gear-second read <path>")
    print(f"    gear-second search <query>")
    print(f"    gear-second diff")
    print(f"    gear-second run \"<command>\"")
    print(f"    gear-second patch --file <path>")
    print(f"    gear-second handoff")
    print(f"    gear-second log")
    print()
    log_event(session_dir, "mode_selected", "local")
    return 0


# ── Phase 3 commands ──────────────────────────────────────────────────────────

def cmd_read(ctx: RepoContext, path: str) -> int:
    from gear_second.repo_tools import read_file
    from gear_second.session import require_session_dir
    from gear_second.logger import log_event

    session_dir = require_session_dir()
    classification, content, warning = read_file(path, ctx.repo_root)

    ui.header()
    ui.section(f"Read: {path}")
    ui.row("Classification", classification.upper(),
           warn=classification in ("protected", "human_only"))
    if warning:
        ui.warn(warning)
    if content:
        print()
        ui.block(content, max_lines=300)
    else:
        ui.warn("No content returned.")

    log_event(session_dir, "file_read", f"path={path} classification={classification}")
    return 0 if content is not None else 1


def cmd_search(ctx: RepoContext, query: str) -> int:
    from gear_second.repo_tools import search_repo
    from gear_second.session import require_session_dir
    from gear_second.logger import log_event

    if not ctx.repo_root:
        ui.error("Not in a git repo — search requires a repo root.")
        return 1

    session_dir = require_session_dir()
    ui.header()
    ui.section(f"Search: {query!r}")

    results = search_repo(query, ctx.repo_root)
    if not results:
        print(f"  {ui.DIM}No matches found.{ui.RESET}")
    else:
        for filepath, lineno, line_content in results:
            loc = f"{filepath}:{lineno}" if lineno else filepath
            print(f"  {ui.CYAN}{loc}{ui.RESET}  {ui.DIM}{line_content[:120]}{ui.RESET}")

    print(f"\n  {len(results)} result(s)")
    log_event(session_dir, "search_run", f"query={query!r} hits={len(results)}")
    return 0


def cmd_diff(ctx: RepoContext) -> int:
    from gear_second.repo_tools import git_diff
    from gear_second.session import require_session_dir
    from gear_second.logger import log_event

    if not ctx.repo_root:
        ui.error("Not in a git repo.")
        return 1

    session_dir = require_session_dir()
    diff_text, changed_files = git_diff(ctx.repo_root)

    ui.header()
    ui.section("Git Diff")
    if changed_files:
        ui.section("Changed Files")
        for f in changed_files:
            cls = classify_path(f)
            warn = cls in ("protected", "human_only")
            ui.row(f, cls.upper(), warn=warn)
    print()
    ui.block(diff_text, max_lines=200)

    log_event(session_dir, "command_run",
              f"git diff — {len(changed_files)} file(s) changed")
    return 0


def cmd_run(ctx: RepoContext, command: str) -> int:
    from gear_second.runner import run_command
    from gear_second.session import require_session_dir
    from gear_second.logger import log_event

    session_dir = require_session_dir()
    ui.header()
    ui.section(f"Run: {command!r}")

    exit_code, stdout, stderr, summary = run_command(
        command, cwd=ctx.repo_root or ctx.cwd
    )

    if stdout:
        ui.section("stdout")
        ui.block(stdout)
    if stderr:
        ui.section("stderr")
        ui.block(stderr)

    ui.section("Result")
    if exit_code == 0:
        ui.ok(summary)
    else:
        ui.warn(summary)

    log_event(session_dir, "command_run",
              f"cmd={command!r} exit={exit_code}")
    return exit_code


def cmd_handoff(ctx: RepoContext) -> int:
    from gear_second.session import require_session_dir, get_current_session_dir
    from gear_second.handoff import write_summary, write_handoff, append_routing_log
    from gear_second.logger import log_event, read_log
    from gear_second.models import SessionState
    import json

    session_dir = require_session_dir()

    # Load existing session state if available
    session_json = session_dir / "session.json"
    if session_json.exists():
        data = json.loads(session_json.read_text(encoding="utf-8"))
        state = SessionState(**{k: v for k, v in data.items()
                                if k in SessionState.__dataclass_fields__})
    else:
        # Minimal state from context
        state = SessionState(
            session_id=session_dir.name,
            created_at_utc="",
            updated_at_utc="",
            venture=ctx.venture,
            repo_path=ctx.repo_root or ctx.cwd,
            repo_name=(ctx.repo_root or ctx.cwd).split("/")[-1],
            branch=ctx.branch,
            task_id=ctx.task_id,
            mode=ctx.mode,
            governance_sources=ctx.governance.sources_loaded,
            session_dir=str(session_dir),
        )

    # Interactive prompts
    ui.header()
    ui.section("Handoff Generator")
    print()

    def prompt(label: str, default: str = "") -> str:
        try:
            val = input(f"  {label}: ").strip()
            return val or default
        except (EOFError, KeyboardInterrupt):
            return default

    work_done = prompt("Work completed (brief)", "(see events.log)")
    blocked = prompt("Blocked / unresolved", "(none)")
    next_step = prompt("Recommended next step", "(continue session)")

    state.status = "handoff_ready"

    summary_path = write_summary(state, notes=work_done)
    handoff_path = write_handoff(
        state,
        work_done=work_done,
        blocked=blocked,
        next_step=next_step,
    )
    state.handoff_path = str(handoff_path)

    append_routing_log(state,
        f"venture={ctx.venture} repo={ctx.repo_root} handoff={handoff_path}")
    log_event(session_dir, "handoff_created", f"path={handoff_path}")

    ui.ok(f"Handoff written: {handoff_path}")
    ui.ok(f"Summary written: {summary_path}")
    ui.ok("ROUTING_LOG.md updated.")
    return 0


def cmd_log(ctx: RepoContext) -> int:
    from gear_second.session import require_session_dir
    from gear_second.logger import read_log

    session_dir = require_session_dir()
    ui.header()
    ui.section(f"Events Log — {session_dir.name}")
    print()
    print(read_log(session_dir))
    return 0


# ── Phase 4 commands ──────────────────────────────────────────────────────────

def cmd_patch(ctx: RepoContext, file_path: str) -> int:
    from gear_second.patcher import patch_file, PatchDenied, PatchAborted
    from gear_second.session import require_session_dir
    from gear_second.logger import log_event

    session_dir = require_session_dir()

    try:
        message, applied = patch_file(file_path, repo_root=ctx.repo_root, interactive=True)
        if applied:
            ui.ok(message)
            log_event(session_dir, "patch_applied", f"file={file_path}")
        else:
            ui.warn(message)
            log_event(session_dir, "patch_drafted", f"file={file_path} applied=false")
        return 0

    except PatchDenied as e:
        ui.error(str(e))
        log_event(session_dir, "protected_write_denied", f"file={file_path} reason={e}")
        return 1

    except PatchAborted as e:
        ui.warn(str(e))
        log_event(session_dir, "write_denied", f"file={file_path} reason=aborted")
        return 0


# ── Parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gear-second",
        description="Gear Second — P51 Brain governed failover mode",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Common options
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--venture", "-v", default=None, help="Override venture name")
    common.add_argument("--task", "-t", default=None, help="Task ID")
    common.add_argument("--mode", "-m", default="auto",
                        choices=["auto", "claude-ollama", "local"],
                        help="Operating mode")

    sub = parser.add_subparsers(dest="command")

    # status (default)
    sub.add_parser("status", parents=[common], help="Show repo, branch, venture, governance")

    # brief
    sub.add_parser("brief", parents=[common], help="Concise project/task summary")

    # start
    p_start = sub.add_parser("start", parents=[common], help="Start a governed session")

    # read
    p_read = sub.add_parser("read", parents=[common], help="Read a file with path classification")
    p_read.add_argument("path", help="File path to read")

    # search
    p_search = sub.add_parser("search", parents=[common], help="Search repo contents")
    p_search.add_argument("query", help="Search query (regex)")

    # diff
    sub.add_parser("diff", parents=[common], help="Show git diff summary")

    # run
    p_run = sub.add_parser("run", parents=[common], help="Run a shell command")
    p_run.add_argument("shell_command", metavar="command", help="Command to run (quote it)")

    # patch
    p_patch = sub.add_parser("patch", parents=[common], help="Safe patch workflow")
    p_patch.add_argument("--file", "-f", required=True, dest="patch_file", help="File to patch")

    # handoff
    sub.add_parser("handoff", parents=[common], help="Generate handoff.md and summary.md")

    # log
    sub.add_parser("log", parents=[common], help="Show session events log")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Default to status if no subcommand given
    if not args.command:
        args.command = "status"

    ctx = load_context(
        venture=getattr(args, "venture", None),
        task_id=getattr(args, "task", None),
        mode=getattr(args, "mode", "auto"),
    )

    command = args.command

    if command == "status":
        return cmd_status(ctx)
    elif command == "brief":
        return cmd_brief(ctx)
    elif command == "start":
        return cmd_start(ctx, mode=args.mode)
    elif command == "read":
        return cmd_read(ctx, args.path)
    elif command == "search":
        return cmd_search(ctx, args.query)
    elif command == "diff":
        return cmd_diff(ctx)
    elif command == "run":
        return cmd_run(ctx, args.shell_command)
    elif command == "patch":
        return cmd_patch(ctx, args.patch_file)
    elif command == "handoff":
        return cmd_handoff(ctx)
    elif command == "log":
        return cmd_log(ctx)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
