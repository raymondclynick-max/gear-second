"""
ui.py — Gear Second Phases 1–5
Terminal output helpers. Minimal, sharp, technical.
Colour-safe: degrades cleanly if terminal doesn't support ANSI.
"""
import sys
import os

# Detect colour support
_COLOUR = (
    hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    and os.environ.get("TERM", "") not in ("dumb", "")
    and os.environ.get("NO_COLOR", "") == ""
)


def _c(code: str) -> str:
    return code if _COLOUR else ""


RESET  = _c("\033[0m")
BOLD   = _c("\033[1m")
DIM    = _c("\033[2m")
RED    = _c("\033[91m")
YELLOW = _c("\033[93m")
GREEN  = _c("\033[92m")
CYAN   = _c("\033[96m")
WHITE  = _c("\033[97m")

# Restrained skull/crossbones + small crab motif. Terminal-first. No clutter.
ASCII_HEADER = f"""{BOLD}{WHITE}
  ╔══════════════════════════════════════════════╗
  ║  ☠  G E A R   S E C O N D  ☠          🦀   ║
  ║  P51 Brain · Governed Failover Mode          ║
  ╚══════════════════════════════════════════════╝{RESET}
"""


def header() -> None:
    print(ASCII_HEADER)


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}── {title}{RESET}")


def row(label: str, value=None, warn: bool = False) -> None:
    colour = YELLOW if warn else WHITE
    val = str(value) if value is not None else f"{DIM}—{RESET}"
    print(f"  {DIM}{label:<26}{RESET}{colour}{val}{RESET}")


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET}  {msg}")


def error(msg: str) -> None:
    print(f"  {RED}✗{RESET}  {msg}", file=sys.stderr)


def block(content: str, max_lines: int = 50) -> None:
    lines = content.splitlines()
    if len(lines) > max_lines:
        shown = lines[:max_lines]
        print("\n".join(f"    {DIM}{l}{RESET}" for l in shown))
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")
    else:
        print("\n".join(f"    {DIM}{l}{RESET}" for l in lines))


def divider() -> None:
    print(f"  {DIM}{'─' * 52}{RESET}")
