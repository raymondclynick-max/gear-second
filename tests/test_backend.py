"""
test_backend.py — Phase 5
Tests for Ollama availability checks and mode selection.
"""
import json
from unittest.mock import patch, MagicMock
from urllib.error import URLError

from gear_second.ollama_adapter import check_ollama
from gear_second.backend import select_mode, mode_a_ready


class TestCheckOllama:
    def test_ollama_running_model_available(self):
        payload = json.dumps({
            "models": [{"name": "gemma4:e4b"}, {"name": "llama3:8b"}]
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("gear_second.ollama_adapter.urlopen", return_value=mock_resp):
            status = check_ollama(model="gemma4:e4b")

        assert status.running is True
        assert status.model_available is True
        assert status.error is None

    def test_ollama_running_model_missing(self):
        payload = json.dumps({"models": [{"name": "llama3:8b"}]}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("gear_second.ollama_adapter.urlopen", return_value=mock_resp):
            status = check_ollama(model="gemma4:e4b")

        assert status.running is True
        assert status.model_available is False
        assert status.error is not None

    def test_ollama_not_running(self):
        with patch("gear_second.ollama_adapter.urlopen", side_effect=URLError("refused")):
            status = check_ollama(model="gemma4:e4b")

        assert status.running is False
        assert status.model_available is False
        assert status.error is not None

    def test_mode_a_ready_false_when_model_missing(self):
        payload = json.dumps({"models": []}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("gear_second.ollama_adapter.urlopen", return_value=mock_resp):
            status = check_ollama(model="gemma4:e4b")

        assert mode_a_ready(status) is False


class TestSelectMode:
    def _mock_ready(self):
        payload = json.dumps({
            "models": [{"name": "gemma4:e4b"}]
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def _mock_unavailable(self):
        return URLError("refused")

    def test_auto_falls_back_to_local_when_ollama_down(self):
        with patch("gear_second.ollama_adapter.urlopen", side_effect=URLError("refused")):
            mode, status = select_mode("auto")
        assert mode == "local"
        assert status.running is False

    def test_auto_selects_claude_ollama_when_ready(self):
        with patch("gear_second.ollama_adapter.urlopen", return_value=self._mock_ready()):
            mode, status = select_mode("auto")
        assert mode == "claude-ollama"

    def test_local_always_returns_local(self):
        with patch("gear_second.ollama_adapter.urlopen", return_value=self._mock_ready()):
            mode, _ = select_mode("local")
        assert mode == "local"

    def test_claude_ollama_explicit(self):
        with patch("gear_second.ollama_adapter.urlopen", return_value=self._mock_ready()):
            mode, status = select_mode("claude-ollama")
        assert mode == "claude-ollama"
        assert mode_a_ready(status) is True
