"""
runner.py — Phase 3
Controlled shell execution with stdout/stderr/exit capture.
"""
import subprocess
import shlex
from typing import Optional, Tuple
from datetime import datetime, timezone


MAX_OUTPUT_LINES = 100


def run_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 60,
) -> Tuple[int, str, str, str]:
    """
    Run a shell command safely.
    Returns (exit_code, stdout, stderr, summary).
    """
    try:
        args = shlex.split(command)
    except ValueError as e:
        return 1, "", str(e), f"Parse error: {e}"

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        stdout = _truncate(result.stdout)
        stderr = _truncate(result.stderr)
        summary = _summarise(command, result.returncode, stdout, stderr)
        return result.returncode, stdout, stderr, summary

    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout}s", f"TIMEOUT: {command}"
    except FileNotFoundError as e:
        return 127, "", str(e), f"Command not found: {args[0] if args else command}"
    except Exception as e:
        return 1, "", str(e), f"Execution error: {e}"


def _truncate(text: str) -> str:
    lines = text.splitlines()
    if len(lines) > MAX_OUTPUT_LINES:
        kept = lines[:MAX_OUTPUT_LINES]
        kept.append(f"... ({len(lines) - MAX_OUTPUT_LINES} more lines truncated)")
        return "\n".join(kept)
    return text


def _summarise(command: str, exit_code: int, stdout: str, stderr: str) -> str:
    status = "OK" if exit_code == 0 else f"FAILED (exit {exit_code})"
    out_lines = len(stdout.splitlines())
    err_lines = len(stderr.splitlines())
    parts = [f"{status} — {command!r}"]
    if out_lines:
        parts.append(f"{out_lines} line(s) stdout")
    if err_lines:
        parts.append(f"{err_lines} line(s) stderr")
    return ", ".join(parts)
