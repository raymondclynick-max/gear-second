"""
repo_tools.py — Phase 3
File reading with path classification, ripgrep search, git diff.
"""
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

from gear_second.governance import classify_path


MAX_READ_LINES = 300


def read_file(path: str, repo_root: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Read a file, returning (classification, content, warning).
    classification: open | caution | protected | human_only
    content: file text (empty string if blocked)
    warning: warning message or empty string
    """
    classification = classify_path(path)
    p = Path(path)

    if classification == "human_only":
        return classification, "", f"BLOCKED: {path} is classified human_only — access denied."

    if not p.exists():
        # Try relative to repo root
        if repo_root:
            p = Path(repo_root) / path
        if not p.exists():
            return classification, "", f"File not found: {path}"

    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    truncated = False
    if len(lines) > MAX_READ_LINES:
        lines = lines[:MAX_READ_LINES]
        truncated = True

    warning = ""
    if classification == "protected":
        warning = f"CAUTION: {path} is a protected path — write operations denied by default."
    elif classification == "caution":
        warning = f"NOTE: {path} is a caution path — writes require confirmation."
    if truncated:
        warning += f" (truncated at {MAX_READ_LINES} lines)"

    return classification, "\n".join(lines), warning


def search_repo(query: str, repo_root: str, max_results: int = 50) -> List[Tuple[str, int, str]]:
    """
    Search repo with ripgrep (falls back to grep).
    Returns list of (filepath, line_number, line_content).
    """
    results = []

    # Try ripgrep first
    rg = shutil.which("rg")
    grep = shutil.which("grep")

    if rg:
        cmd = [rg, "--line-number", "--no-heading", "--max-count=5",
               f"--max-filesize=1M", query, repo_root]
    elif grep:
        cmd = [grep, "-rn", "--include=*.py", "--include=*.ts", "--include=*.tsx",
               "--include=*.js", "--include=*.md", "--include=*.yaml", "--include=*.yml",
               query, repo_root]
    else:
        return results

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            cwd=repo_root
        )
        for line in proc.stdout.splitlines()[:max_results]:
            parts = line.split(":", 2)
            if len(parts) >= 3:
                filepath, lineno_str, content = parts[0], parts[1], parts[2]
                try:
                    results.append((filepath, int(lineno_str), content.strip()))
                except ValueError:
                    pass
            elif len(parts) == 2:
                results.append((parts[0], 0, parts[1]))
    except subprocess.TimeoutExpired:
        results.append(("(search timed out)", 0, ""))

    return results


def git_diff(repo_root: str, staged: bool = False) -> Tuple[str, List[str]]:
    """
    Get git diff. Returns (diff_text, changed_files).
    """
    cmd_diff = ["git", "diff"]
    if staged:
        cmd_diff.append("--cached")

    cmd_files = ["git", "diff", "--name-only"]
    if staged:
        cmd_files.append("--cached")

    try:
        diff_result = subprocess.run(
            cmd_diff, capture_output=True, text=True, cwd=repo_root, timeout=10
        )
        files_result = subprocess.run(
            cmd_files, capture_output=True, text=True, cwd=repo_root, timeout=10
        )
        diff_text = diff_result.stdout or "(no unstaged changes)"
        changed = [f for f in files_result.stdout.splitlines() if f.strip()]
        return diff_text, changed
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "(git diff unavailable)", []
