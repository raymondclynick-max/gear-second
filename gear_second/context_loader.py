"""
context_loader.py — Phase 1–5
Detects repo root, git branch, venture name, and loads governance files.
Graceful degradation: continues with conservative defaults if governance
files or git are missing.
"""
from pathlib import Path
import subprocess
from typing import Optional
import os

from gear_second.models import RepoContext, GovernanceInfo

BRAIN_DIR = Path.home() / ".claude"

GOVERNANCE_FILES = {
    "routing_policy": "ROUTING_POLICY.md",
    "system_boundaries": "SYSTEM_BOUNDARIES.md",
    "open_tasks": "OPEN_TASKS.md",
    "routing_log": "ROUTING_LOG.md",
}

VENTURE_MAP = {
    "icy": "ICY Development Map",
    "icy-development-map": "ICY Development Map",
    "oro": "ORO Spirits",
    "cask-amber": "Cask & Amber",
    "kalimera": "Kalimera.ai",
    "kyanolab": "KyanoLab",
    "relocate-cy": "Relocate.CY",
    "tracechain": "TraceChain",
    "mycohere": "MycoHero",
    "creavolt": "CreaVolt",
    "lourelle": "Lourelle",
    "elixir": "Elixir of the Med",
    "orea": "Ōrea",
    "doodle-flick": "Doodle Flick",
    "nigel": "N.I.G.E.L.",
    "gear-second": "Gear Second",
}


def _run(cmd: list[str], cwd: Optional[str] = None) -> Optional[str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # git not installed or timeout — graceful degradation
        return None


def detect_repo_root(cwd: Optional[str] = None) -> Optional[str]:
    return _run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)


def detect_branch(repo_root: Optional[str] = None) -> Optional[str]:
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)


def detect_recent_changes(repo_root: Optional[str] = None) -> list[str]:
    out = _run(["git", "log", "--oneline", "-10"], cwd=repo_root)
    if out:
        return out.splitlines()
    return []


def detect_venture(repo_root: Optional[str] = None, cwd: Optional[str] = None) -> Optional[str]:
    """Infer venture from repo directory name or path."""
    check_path = repo_root or cwd or os.getcwd()
    path = Path(check_path)
    # Check directory name and parents
    for part in [path.name, path.parent.name]:
        slug = part.lower().replace("_", "-")
        if slug in VENTURE_MAP:
            return VENTURE_MAP[slug]
        for key in VENTURE_MAP:
            if key in slug:
                return VENTURE_MAP[key]
    return None


def load_governance(venture: Optional[str] = None) -> GovernanceInfo:
    gov = GovernanceInfo()
    missing = []

    # Load brain-level governance files
    for attr, filename in GOVERNANCE_FILES.items():
        path = BRAIN_DIR / filename
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if attr == "routing_log":
                # Only load tail (last 30 lines) — full log can be large
                lines = content.splitlines()
                gov.routing_log_tail = "\n".join(lines[-30:])
            else:
                setattr(gov, attr, content)
            gov.sources_loaded.append(str(path))
        else:
            missing.append(filename)

    # Load venture-specific CLAUDE.md if venture known
    if venture:
        venture_slug = venture.lower().replace(" ", "-").replace(".", "").replace("/", "-")
        # Map back to filesystem slug
        for slug, name in VENTURE_MAP.items():
            if name == venture:
                venture_slug = slug
                break
        venture_path = BRAIN_DIR / "ventures" / venture_slug / "CLAUDE.md"
        if venture_path.exists():
            try:
                # Load first 200 lines only (can be very large)
                lines = venture_path.read_text(encoding="utf-8", errors="replace").splitlines()
                gov.venture_claude_md = "\n".join(lines[:200])
                gov.sources_loaded.append(str(venture_path))
            except OSError:
                missing.append(f"ventures/{venture_slug}/CLAUDE.md (read error)")
        else:
            missing.append(f"ventures/{venture_slug}/CLAUDE.md")

    gov.missing = missing
    return gov


def load_context(
    cwd: Optional[str] = None,
    venture: Optional[str] = None,
    task_id: Optional[str] = None,
    mode: str = "auto",
) -> RepoContext:
    cwd = cwd or os.getcwd()
    repo_root = detect_repo_root(cwd)
    branch = detect_branch(repo_root) if repo_root else None
    detected_venture = venture or detect_venture(repo_root, cwd)
    recent_changes = detect_recent_changes(repo_root) if repo_root else []
    governance = load_governance(detected_venture)

    ctx = RepoContext(
        cwd=cwd,
        repo_root=repo_root,
        is_git_repo=repo_root is not None,
        branch=branch,
        venture=detected_venture,
        task_id=task_id,
        mode=mode,
        governance=governance,
        recent_changes=recent_changes,
    )
    return ctx
