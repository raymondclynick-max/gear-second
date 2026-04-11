"""
ollama_adapter.py — Phase 2
Check Ollama availability and prepare Claude Code via Ollama gateway.
"""
import os
import subprocess
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

from gear_second.models import OllamaStatus

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
TARGET_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")


def check_ollama(host: str = OLLAMA_HOST, model: str = TARGET_MODEL) -> OllamaStatus:
    """Check if Ollama is running and the target model is available."""
    status = OllamaStatus(host=host, model_name=model)

    # Check if Ollama is reachable
    try:
        req = Request(f"{host}/api/tags", headers={"Accept": "application/json"})
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        status.running = True
    except (URLError, OSError, json.JSONDecodeError) as e:
        status.running = False
        status.error = f"Ollama not reachable at {host}: {e}"
        return status

    # Check if target model is available
    models = data.get("models", [])
    available_names = [m.get("name", "") for m in models]
    # Match exact or prefix (e.g. "gemma4:e4b" matches "gemma4:e4b")
    status.model_available = any(
        name == model or name.startswith(model.split(":")[0])
        for name in available_names
    )
    if not status.model_available:
        status.error = (
            f"Model '{model}' not found in Ollama. "
            f"Available: {', '.join(available_names) or 'none'}"
        )
    return status


def prepare_mode_a_env(host: str = OLLAMA_HOST) -> dict:
    """Return environment variables for Claude Code via Ollama gateway."""
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = f"{host}/v1"
    env["ANTHROPIC_API_KEY"] = "ollama"
    return env


def launch_claude_via_ollama(
    repo_path: Optional[str] = None,
    host: str = OLLAMA_HOST,
) -> int:
    """
    Launch Claude Code with Ollama as the ANTHROPIC backend.
    Returns the exit code of the claude process.
    """
    import shutil

    claude_bin = shutil.which("claude")
    if not claude_bin:
        raise RuntimeError(
            "claude binary not found in PATH. "
            "Ensure Claude Code CLI is installed: npm install -g @anthropic-ai/claude-code"
        )

    env = prepare_mode_a_env(host)
    cwd = repo_path or os.getcwd()

    result = subprocess.run([claude_bin], env=env, cwd=cwd)
    return result.returncode
