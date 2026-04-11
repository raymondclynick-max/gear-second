"""
governance.py — Phase 1
Reads governance files and classifies path authority.
"""
from pathlib import Path
from typing import Optional
from gear_second.models import RepoContext

# Path classification — order matters: most restrictive to least
HUMAN_ONLY_PATTERNS = [
    ".env", ".env.local", "secrets/", "credentials/", "production/", "prod/",
]
PROTECTED_PATTERNS = [
    "backend/", "api/", "db/", "database/", "supabase/", "migrations/",
    "infra/", ".env",
]
CAUTION_PATTERNS = [
    "src/", "scripts/", ".github/", "config/", "configs/", "tools/",
    "scraper/", "reconcile/", "crawlers/", "outreach/",
]
OPEN_PATTERNS = [
    "docs/", "README", "tests/", "examples/", "reports/",
]

# Brain-level governance files are always protected
BRAIN_GOVERNANCE_FILES = {
    "CLAUDE.md", "ROUTING_POLICY.md", "SYSTEM_BOUNDARIES.md",
    "ROUTING_LOG.md", "DECISIONS_LOG.md", "OPEN_TASKS.md",
    "CLOSED_TASKS.md", "ANTIGRAVITY.md", "MERGE_CHECKLIST.md",
    "EMERGENCY_OVERRIDE.md",
}


def classify_path(path: str) -> str:
    """Return: human_only | protected | caution | open"""
    p = path.replace("\\", "/")
    name = Path(p).name

    # Brain governance files
    if name in BRAIN_GOVERNANCE_FILES:
        return "protected"

    # Secrets and credentials
    if name.startswith(".env") or any(pat in p for pat in HUMAN_ONLY_PATTERNS):
        return "human_only"

    # Protected backend paths
    if any(pat in p for pat in PROTECTED_PATTERNS):
        return "protected"

    # Caution — needs confirmation
    if any(pat in p for pat in CAUTION_PATTERNS):
        return "caution"

    # Default open
    return "open"


def write_allowed(path: str, classification: Optional[str] = None) -> bool:
    """Returns True if write is allowed by default governance."""
    cls = classification or classify_path(path)
    return cls == "open"


def get_write_authority_summary(ctx: RepoContext) -> str:
    lines = [
        "Write authority (Gear Second Phase 1 defaults):",
        "  OPEN paths       — read + write with confirmation",
        "  CAUTION paths    — read + write with warning + log",
        "  PROTECTED paths  — read only, write denied by default",
        "  HUMAN_ONLY paths — access blocked",
        "",
        "Merge to main: DENIED (default)",
        "DB mutations:  DENIED (default)",
        "Protected-path writes: DENIED (default)",
    ]
    return "\n".join(lines)


def get_missing_governance_note(ctx: RepoContext) -> str:
    missing = ctx.governance.missing
    if not missing:
        return "All expected governance files loaded."
    return f"Missing governance files ({len(missing)}): {', '.join(missing)}"
