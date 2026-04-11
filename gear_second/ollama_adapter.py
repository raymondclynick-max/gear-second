"""
ollama_adapter.py — Phase 2
Check Ollama availability and prepare Claude Code via LiteLLM + Ollama gateway.

Mode A flow:
  1. Start LiteLLM proxy (port 4000) pointing at Ollama
  2. Set ANTHROPIC_BASE_URL=http://localhost:4000 + ANTHROPIC_API_KEY=dummy
  3. Launch Claude Code — it speaks to LiteLLM which speaks to Ollama
"""
import os
import subprocess
import shutil
import time
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

from gear_second.models import OllamaStatus

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
TARGET_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")

LITELLM_PORT = int(os.environ.get("LITELLM_PORT", "4000"))
LITELLM_BASE_URL = f"http://localhost:{LITELLM_PORT}"

# Locate the litellm config relative to this package's repo root
_HERE = Path(__file__).parent
LITELLM_CONFIG = os.environ.get(
    "LITELLM_CONFIG",
    str(_HERE.parent / "litellm_config.yaml"),
)

# PID file so we only start one LiteLLM instance per machine session
_LITELLM_PID_FILE = Path("/tmp/gear_second_litellm.pid")


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


def _litellm_running() -> bool:
    """Return True if a LiteLLM proxy is already listening on LITELLM_PORT."""
    try:
        req = Request(f"{LITELLM_BASE_URL}/health")
        with urlopen(req, timeout=2):
            return True
    except Exception:
        return False


def _start_litellm() -> Optional[int]:
    """
    Start LiteLLM proxy in the background if not already running.
    Tracks the PID in /tmp/gear_second_litellm.pid.
    Returns the PID, or None if LiteLLM binary is unavailable.
    """
    # Already running? (either by us or externally)
    if _litellm_running():
        if _LITELLM_PID_FILE.exists():
            try:
                return int(_LITELLM_PID_FILE.read_text().strip())
            except (ValueError, OSError):
                pass
        return None  # external — not our PID to track

    litellm_bin = shutil.which("litellm")
    if not litellm_bin:
        return None

    if not Path(LITELLM_CONFIG).exists():
        return None

    proc = subprocess.Popen(
        [litellm_bin, "--config", LITELLM_CONFIG, "--port", str(LITELLM_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _LITELLM_PID_FILE.write_text(str(proc.pid))

    # Wait up to 15s for proxy to become ready
    for _ in range(15):
        time.sleep(1)
        if _litellm_running():
            return proc.pid

    # Timed out — kill it and signal failure
    proc.kill()
    _LITELLM_PID_FILE.unlink(missing_ok=True)
    return None


def prepare_mode_a_env() -> dict:
    """Return environment variables for Claude Code via LiteLLM proxy."""
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = LITELLM_BASE_URL
    env["ANTHROPIC_API_KEY"] = "dummy"
    return env


def launch_claude_via_ollama(
    repo_path: Optional[str] = None,
    host: str = OLLAMA_HOST,  # kept for API compatibility; LiteLLM mediates now
) -> int:
    """
    Start LiteLLM (if needed), then launch Claude Code via the LiteLLM proxy.
    Returns the exit code of the claude process.
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        raise RuntimeError(
            "claude binary not found in PATH. "
            "Ensure Claude Code CLI is installed: npm install -g @anthropic-ai/claude-code"
        )

    litellm_pid = _start_litellm()
    if litellm_pid is None and not _litellm_running():
        raise RuntimeError(
            f"LiteLLM proxy could not start on port {LITELLM_PORT}. "
            f"Check that litellm is installed and {LITELLM_CONFIG} exists."
        )

    env = prepare_mode_a_env()
    cwd = repo_path or os.getcwd()

    result = subprocess.run([claude_bin], env=env, cwd=cwd)
    return result.returncode
