"""
test_patcher.py — Phase 5
Tests for path classification, patch deny on protected/human_only paths.
"""
import pytest
from pathlib import Path

from gear_second.governance import classify_path, write_allowed
from gear_second.patcher import PatchDenied, patch_file, dry_run_diff


class TestClassifyPath:
    def test_env_is_human_only(self):
        assert classify_path(".env") == "human_only"

    def test_env_local_is_human_only(self):
        assert classify_path(".env.local") == "human_only"

    def test_secrets_dir_is_human_only(self):
        assert classify_path("secrets/api_key.txt") == "human_only"

    def test_supabase_is_protected(self):
        assert classify_path("supabase/migrations/001.sql") == "protected"

    def test_backend_is_protected(self):
        assert classify_path("backend/server.py") == "protected"

    def test_src_is_caution(self):
        assert classify_path("src/components/Map.tsx") == "caution"

    def test_scraper_is_caution(self):
        assert classify_path("scraper/scraper.py") == "caution"

    def test_docs_is_open(self):
        assert classify_path("docs/README.md") == "open"

    def test_tests_is_open(self):
        assert classify_path("tests/test_foo.py") == "open"

    def test_readme_is_open(self):
        assert classify_path("README.md") == "open"

    def test_brain_governance_is_protected(self):
        assert classify_path("CLAUDE.md") == "protected"
        assert classify_path("ROUTING_POLICY.md") == "protected"
        assert classify_path("SYSTEM_BOUNDARIES.md") == "protected"


class TestWriteAllowed:
    def test_open_allowed(self):
        assert write_allowed("docs/README.md") is True

    def test_protected_denied(self):
        assert write_allowed("backend/server.py") is False

    def test_human_only_denied(self):
        assert write_allowed(".env") is False

    def test_caution_denied_by_default(self):
        # caution paths are not freely writable without confirmation
        assert write_allowed("src/components/Map.tsx") is False


class TestPatchDeny:
    def test_human_only_raises_patch_denied(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=abc\n")
        with pytest.raises(PatchDenied, match="human_only"):
            patch_file(str(env_file), repo_root=str(tmp_path), interactive=False)

    def test_protected_raises_patch_denied(self, tmp_path):
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        server = backend_dir / "server.py"
        server.write_text("# server\n")
        with pytest.raises(PatchDenied, match="protected"):
            patch_file(str(server), repo_root=str(tmp_path), interactive=False)

    def test_open_path_non_interactive_raises_aborted(self, tmp_path):
        from gear_second.patcher import PatchAborted
        readme = tmp_path / "README.md"
        readme.write_text("# Hello\n")
        with pytest.raises(PatchAborted):
            patch_file(str(readme), repo_root=str(tmp_path), interactive=False)


class TestDryRunDiff:
    def test_diff_shows_change(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello\n")
        cls, diff = dry_run_diff(str(f), "# Hello\n# World\n", repo_root=str(tmp_path))
        assert cls == "open"
        assert "+# World" in diff

    def test_no_diff_for_identical_content(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Hello\n")
        cls, diff = dry_run_diff(str(f), "# Hello\n", repo_root=str(tmp_path))
        assert diff == ""

    def test_protected_path_classified_correctly(self, tmp_path):
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        f = backend_dir / "server.py"
        f.write_text("# original\n")
        cls, diff = dry_run_diff(str(f), "# modified\n", repo_root=str(tmp_path))
        assert cls == "protected"
