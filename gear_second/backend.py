"""
backend.py — Phase 2
Mode selection: auto -> try Mode A (Claude/Ollama), fall back to Mode B (local).
"""
from typing import Tuple

from gear_second.models import OllamaStatus
from gear_second.ollama_adapter import check_ollama, OLLAMA_HOST, TARGET_MODEL


def select_mode(requested: str) -> Tuple[str, OllamaStatus]:
    """
    Resolve the operating mode.
    Returns (resolved_mode, ollama_status).
    resolved_mode: "claude-ollama" | "local"
    """
    ollama = check_ollama(OLLAMA_HOST, TARGET_MODEL)

    if requested == "claude-ollama":
        return "claude-ollama", ollama

    if requested == "local":
        return "local", ollama

    # auto: try Mode A, fall back to Mode B
    if ollama.running and ollama.model_available:
        return "claude-ollama", ollama
    return "local", ollama


def mode_a_ready(ollama: OllamaStatus) -> bool:
    return ollama.running and ollama.model_available


def mode_summary(mode: str, ollama: OllamaStatus) -> str:
    if mode == "claude-ollama":
        if mode_a_ready(ollama):
            return f"Mode A — Claude Code via Ollama ({ollama.model_name} @ {ollama.host})"
        return f"Mode A requested but unavailable: {ollama.error}"
    return "Mode B — Local wrapper"
