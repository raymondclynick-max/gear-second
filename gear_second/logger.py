"""
logger.py — Phase 2
Append-only events.log writer for session directories.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


VALID_EVENT_TYPES = {
    "session_start", "session_resume", "mode_selected", "governance_loaded",
    "governance_conflict", "command_run", "file_read", "search_run",
    "patch_drafted", "patch_applied", "write_denied", "protected_write_denied",
    "handoff_created", "session_complete", "session_blocked", "session_error",
    "context_snapshot",
}


def log_event(
    session_dir: Path,
    event_type: str,
    message: str,
    extra: Optional[str] = None,
) -> None:
    """Append one event line to session_dir/events.log."""
    if event_type not in VALID_EVENT_TYPES:
        event_type = "command_run"  # safe fallback

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{ts} | {event_type} | {message}"
    if extra:
        line += f" | {extra}"

    log_path = Path(session_dir) / "events.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_log(session_dir: Path, tail: int = 30) -> str:
    """Read last N lines of events.log."""
    log_path = Path(session_dir) / "events.log"
    if not log_path.exists():
        return "(no events logged yet)"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-tail:])
