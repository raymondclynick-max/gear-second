"""
patcher.py — Phase 4
Safe patch workflow: read -> classify -> draft diff -> confirm -> apply.
PROTECTED and HUMAN_ONLY paths: deny by default.
OPEN and CAUTION: show diff, require "confirm" typed explicitly.
"""
import difflib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from gear_second.governance import classify_path, write_allowed


class PatchDenied(Exception):
    """Raised when a patch is denied by governance policy."""


class PatchAborted(Exception):
    """Raised when the user does not confirm the patch."""


def read_current(path: str, repo_root: Optional[str] = None) -> Tuple[str, Path]:
    """Read current file content. Returns (content, resolved_path)."""
    p = Path(path)
    if not p.is_absolute() and repo_root:
        p = Path(repo_root) / path
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p.read_text(encoding="utf-8"), p


def make_unified_diff(original: str, revised: str, filename: str) -> str:
    """Generate a unified diff string."""
    orig_lines = original.splitlines(keepends=True)
    rev_lines = revised.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines, rev_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def open_in_editor(content: str, suffix: str = ".txt") -> str:
    """
    Open content in $EDITOR (fallback: nano, then vi).
    Returns the edited content.
    """
    editor = os.environ.get("EDITOR") or shutil.which("nano") or shutil.which("vi") or "vi"
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name
    try:
        subprocess.run([editor, tmp_path], check=False)
        return Path(tmp_path).read_text(encoding="utf-8")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def patch_file(
    path: str,
    repo_root: Optional[str] = None,
    interactive: bool = True,
) -> Tuple[str, bool]:
    """
    Full patch workflow.
    Returns (message, applied: bool).
    Raises PatchDenied on governance block, PatchAborted on user cancel.
    """
    classification = classify_path(path)

    # Governance check
    if classification == "human_only":
        raise PatchDenied(
            f"DENIED: {path} is classified human_only. "
            "Write access blocked by governance policy."
        )
    if classification == "protected":
        raise PatchDenied(
            f"DENIED: {path} is a protected path. "
            "Write access blocked by default governance policy. "
            "If this is intentional, explicit human approval is required."
        )

    # Read current content
    original, resolved = read_current(path, repo_root)

    if not interactive:
        raise PatchAborted("Non-interactive mode: patch requires user interaction.")

    # Open in editor
    print(f"\n  Opening {resolved} in editor...")
    print(f"  Path classification: {classification.upper()}")
    if classification == "caution":
        print(f"  WARNING: This is a caution path. Confirmation required before apply.")
    print()

    revised = open_in_editor(original, suffix=Path(path).suffix or ".txt")

    if revised == original:
        return "No changes made — file unchanged.", False

    # Show diff
    diff_text = make_unified_diff(original, revised, str(resolved))
    if not diff_text.strip():
        return "Diff is empty — no changes to apply.", False

    print("\n" + "─" * 60)
    print(diff_text)
    print("─" * 60)

    # Require explicit confirmation
    print(f"\n  To apply this patch to {resolved}, type 'confirm' and press Enter.")
    print("  Any other input will abort.")
    try:
        answer = input("  > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise PatchAborted("Aborted by user (EOF/interrupt).")

    if answer != "confirm":
        raise PatchAborted("Patch aborted — 'confirm' not typed.")

    # Apply
    resolved.write_text(revised, encoding="utf-8")
    return f"Patch applied to {resolved}.", True


def dry_run_diff(
    path: str,
    new_content: str,
    repo_root: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Return (classification, diff_text) without applying.
    Used in tests and non-interactive flows.
    """
    classification = classify_path(path)
    try:
        original, resolved = read_current(path, repo_root)
    except FileNotFoundError:
        original = ""
        resolved = Path(path)
    diff_text = make_unified_diff(original, new_content, str(resolved))
    return classification, diff_text
