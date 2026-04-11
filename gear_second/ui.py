"""
ui.py — Phase 1
Terminal output helpers. Minimal, sharp, technical.
"""
import sys
from typing import Optional

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
WHITE = "\033[97m"

ASCII_HEADER = r"""
  ╔═══════════════════════════════════════════╗
  ║   ☠  G E A R  S E C O N D  ☠             ║
  ║   P51 Brain · Governed Failover Mode      ║
  ╚═══════════════════════════════════════════╝
"""


def header() -> None:
    print(f"{BOLD}{WHITE}{ASCII_HEADER}{RESET}")


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}── {title}{RESET}")


def row(label: str, value: Optional[str], warn: bool = False) -> None:
    colour = YELLOW if warn else WHITE
    val = value if value else f"{DIM}—{RESET}"
    print(f"  {DIM}{label:<24}{RESET}{colour}{val}{RESET}")


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET}  {msg}", file=sys.stderr)


def error(msg: str) -> None:
    print(f"  {RED}✗{RESET}  {msg}", file=sys.stderr)


def block(content: str, max_lines: int = 20) -> None:
    lines = content.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"{DIM}... ({len(lines) - max_lines} more lines){RESET}"]
    for line in lines:
        print(f"    {DIM}{line}{RESET}")


def divider() -> None:
    print(f"  {DIM}{'─' * 50}{RESET}")
