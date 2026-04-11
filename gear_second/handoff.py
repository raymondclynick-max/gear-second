"""
handoff.py — Phase 3/4
Generate handoff.md and summary.md, append to ROUTING_LOG.md.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json

from gear_second.models import SessionState

BRAIN_DIR = Path.home() / ".claude"


def write_summary(state: SessionState, notes: str = "") -> Path:
    """Write summary.md to session dir. Returns path."""
    session_dir = Path(state.session_dir)
    now = datetime.now(timezone.utc).isoformat()

    lines = [
        f"# Gear Second — Session Summary",
        f"",
        f"**Session ID:** {state.session_id}",
        f"**Status:** {state.status}",
        f"**Started:** {state.created_at_utc}",
        f"**Updated:** {now}",
        f"",
        f"## Session Purpose",
        notes or "(not specified)",
        f"",
        f"## Repo & Task",
        f"- Repo: {state.repo_path}",
        f"- Branch: {state.branch or '—'}",
        f"- Venture: {state.venture or '—'}",
        f"- Task ID: {state.task_id or '—'}",
        f"- Mode: {state.mode}",
        f"- Backend: {state.backend_model or '—'}",
        f"",
        f"## Files Inspected",
    ]
    for f in state.inspected_files:
        lines.append(f"- {f}")
    if not state.inspected_files:
        lines.append("- (none recorded)")

    lines += [f"", f"## Files Changed"]
    for f in state.changed_files:
        lines.append(f"- {f}")
    if not state.changed_files:
        lines.append("- (none)")

    lines += [f"", f"## Commands Run"]
    for c in state.commands_run:
        lines.append(f"- `{c}`")
    if not state.commands_run:
        lines.append("- (none)")

    lines += [f"", f"## Warnings"]
    for w in state.warnings:
        lines.append(f"- {w}")
    if not state.warnings:
        lines.append("- (none)")

    lines += [f"", f"## Unresolved Items", "(see handoff.md)"]

    path = session_dir / "summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_handoff(
    state: SessionState,
    work_done: str = "",
    blocked: str = "",
    next_step: str = "",
    notes: str = "",
) -> Path:
    """Write handoff.md to session dir. Returns path."""
    session_dir = Path(state.session_dir)
    now = datetime.now(timezone.utc).isoformat()

    venture_slug = (state.venture or "unknown").lower().replace(" ", "-")
    repo_name = state.repo_name or "unknown"

    resume_cmd = (
        f"cd {state.repo_path} && gear-second start "
        f"--mode {state.mode}"
        + (f" --venture '{state.venture}'" if state.venture else "")
        + (f" --task {state.task_id}" if state.task_id else "")
    )

    lines = [
        f"# Gear Second — Handoff",
        f"",
        f"**Session ID:** {state.session_id}",
        f"**Generated:** {now}",
        f"**Status:** {state.status}",
        f"",
        f"## Session Metadata",
        f"- Venture: {state.venture or '—'}",
        f"- Repo: {state.repo_path}",
        f"- Branch: {state.branch or '—'}",
        f"- Task ID: {state.task_id or '—'}",
        f"- Mode: {state.mode}",
        f"- Backend: {state.backend_model or '—'}",
        f"",
        f"## Governance Context",
        f"Sources loaded:",
    ]
    for src in state.governance_sources:
        lines.append(f"- {src}")
    if not state.governance_sources:
        lines.append("- (none loaded — conservative defaults applied)")

    lines += [
        f"",
        f"## Work Completed",
        work_done or "(not specified)",
        f"",
        f"## Findings",
        notes or "(none recorded)",
        f"",
        f"## Warnings",
    ]
    for w in state.warnings:
        lines.append(f"- {w}")
    if not state.warnings:
        lines.append("- (none)")

    lines += [
        f"",
        f"## Unresolved / Blocked",
        blocked or "(none recorded)",
        f"",
        f"## Recommended Next Step",
        next_step or "(not specified)",
        f"",
        f"## Suggested Resume Command",
        f"```bash",
        resume_cmd,
        f"```",
    ]

    path = session_dir / "handoff.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def append_routing_log(state: SessionState, message: str) -> None:
    """Append a handoff_created entry to ~/.claude/ROUTING_LOG.md."""
    log_path = BRAIN_DIR / "ROUTING_LOG.md"
    if not log_path.exists():
        return  # Don't create if missing
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"{now} | Gear Second | {state.session_id} | handoff_created | "
        f"{message}"
    )
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")
