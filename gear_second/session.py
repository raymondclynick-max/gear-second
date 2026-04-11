"""
session.py — Phase 2
Session directory creation, session.json, context_snapshot.md.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import re
from typing import Optional

from gear_second.models import RepoContext, SessionState
from gear_second.governance import get_write_authority_summary

SESSIONS_DIR = Path.home() / ".claude" / "gear-second" / "sessions"


def _make_session_id(ctx: RepoContext, mode: str) -> str:
    """YYYYMMDD-HHMMSSz-<venture-slug>-<repo-name>-<mode>"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    venture_slug = re.sub(r"[^a-z0-9]+", "-", (ctx.venture or "unknown").lower()).strip("-")
    repo_slug = re.sub(r"[^a-z0-9]+", "-", (
        Path(ctx.repo_root or ctx.cwd).name
    ).lower()).strip("-")
    mode_slug = mode.replace("-", "")[:12]
    return f"{ts}-{venture_slug[:16]}-{repo_slug[:16]}-{mode_slug}"


def create_session(ctx: RepoContext, mode: str, backend_model: Optional[str] = None) -> SessionState:
    """Create session directory and write initial files. Returns SessionState."""
    now = datetime.now(timezone.utc).isoformat()
    session_id = _make_session_id(ctx, mode)
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    state = SessionState(
        session_id=session_id,
        created_at_utc=now,
        updated_at_utc=now,
        venture=ctx.venture,
        repo_name=Path(ctx.repo_root or ctx.cwd).name,
        repo_path=ctx.repo_root or ctx.cwd,
        branch=ctx.branch,
        task_id=ctx.task_id,
        mode=mode,
        backend_model=backend_model,
        governance_sources=ctx.governance.sources_loaded,
        status="active",
        session_dir=str(session_dir),
    )

    _write_session_json(state, session_dir)
    _write_context_snapshot(state, ctx, session_dir)

    return state


def _write_session_json(state: SessionState, session_dir: Path) -> None:
    import dataclasses
    session_dir.joinpath("session.json").write_text(
        json.dumps(dataclasses.asdict(state), indent=2, default=str),
        encoding="utf-8",
    )


def update_session(state: SessionState) -> None:
    """Persist updated session state."""
    if not state.session_dir:
        return
    session_dir = Path(state.session_dir)
    state.updated_at_utc = datetime.now(timezone.utc).isoformat()
    _write_session_json(state, session_dir)


def _write_context_snapshot(state: SessionState, ctx: RepoContext, session_dir: Path) -> None:
    lines = [
        f"# Gear Second — Context Snapshot",
        f"",
        f"**Session ID:** {state.session_id}",
        f"**Started at:** {state.created_at_utc}",
        f"**Mode:** {state.mode}",
        f"**Backend:** {state.backend_model or '—'}",
        f"",
        f"## Repo",
        f"- Repo: {ctx.repo_root or ctx.cwd}",
        f"- Branch: {ctx.branch or '—'}",
        f"- Venture: {ctx.venture or '—'}",
        f"- Task ID: {ctx.task_id or '—'}",
        f"",
        f"## Governance Sources",
    ]
    for src in ctx.governance.sources_loaded:
        lines.append(f"- {src}")
    if ctx.governance.missing:
        lines.append(f"")
        lines.append(f"### Missing")
        for m in ctx.governance.missing:
            lines.append(f"- {m}")

    lines += [
        f"",
        f"## Write Authority",
        get_write_authority_summary(ctx),
        f"",
        f"## Recent Commits",
    ]
    for c in ctx.recent_changes[:10]:
        lines.append(f"- {c}")

    session_dir.joinpath("context_snapshot.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def get_current_session_dir() -> Optional[Path]:
    """Return the most recently created session dir, or None."""
    if not SESSIONS_DIR.exists():
        return None
    dirs = sorted(SESSIONS_DIR.iterdir(), reverse=True)
    for d in dirs:
        if d.is_dir() and (d / "session.json").exists():
            return d
    return None


def require_session_dir() -> Path:
    """Return current session dir, creating a bare one if needed."""
    d = get_current_session_dir()
    if d:
        return d
    # Create minimal session dir so log/handoff can still work
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    d = SESSIONS_DIR / f"{ts}-nosession"
    d.mkdir(parents=True, exist_ok=True)
    return d
