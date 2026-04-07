"""Tests for charlieverse/paths.py — bundled asset resolution helpers."""

from __future__ import annotations

from unittest.mock import patch

import charlieverse.helpers.paths as paths_mod
from charlieverse.helpers import paths


class TestFind:
    def test_returns_bundled_path_when_exists(self, tmp_path):
        bundled = tmp_path / "pkg" / "web" / "dist"
        bundled.mkdir(parents=True)

        with patch.object(paths_mod, "_PKG_DIR", tmp_path / "pkg"):
            result = paths_mod._find("web/dist")

        assert result == bundled

    def test_falls_back_to_repo_when_bundled_missing(self, tmp_path):
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        repo_dir = tmp_path
        (repo_dir / "web" / "dist").mkdir(parents=True)

        with (
            patch.object(paths_mod, "_PKG_DIR", pkg_dir),
            patch.object(paths_mod, "_REPO_DIR", repo_dir),
        ):
            result = paths_mod._find("web/dist")

        assert result == repo_dir / "web" / "dist"

    def test_returns_none_when_neither_exists(self, tmp_path):
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        with (
            patch.object(paths_mod, "_PKG_DIR", pkg_dir),
            patch.object(paths_mod, "_REPO_DIR", repo_dir),
        ):
            result = paths_mod._find("web/dist")

        assert result is None


class TestWebDist:
    def test_returns_path_when_present(self, tmp_path):
        dist = tmp_path / "web" / "dist"
        dist.mkdir(parents=True)

        with (
            patch.object(paths_mod, "_PKG_DIR", tmp_path),
            patch.object(paths_mod, "_REPO_DIR", tmp_path / "nonexistent"),
        ):
            result = paths.web_dist()

        assert result == dist

    def test_returns_none_when_absent(self, tmp_path):
        with (
            patch.object(paths_mod, "_PKG_DIR", tmp_path),
            patch.object(paths_mod, "_REPO_DIR", tmp_path),
        ):
            result = paths.web_dist()

        assert result is None


class TestIntegration:
    def test_returns_provider_path(self, tmp_path):
        claude_dir = tmp_path / "integrations" / "claude"
        claude_dir.mkdir(parents=True)

        with (
            patch.object(paths_mod, "_PKG_DIR", tmp_path),
            patch.object(paths_mod, "_REPO_DIR", tmp_path / "nonexistent"),
        ):
            result = paths.integration("claude")

        assert result == claude_dir

    def test_returns_none_for_missing_provider(self, tmp_path):
        with (
            patch.object(paths_mod, "_PKG_DIR", tmp_path),
            patch.object(paths_mod, "_REPO_DIR", tmp_path),
        ):
            result = paths.integration("nonexistent_provider")

        assert result is None


class TestToolsScripts:
    def test_prefers_bundled_tools_scripts(self, tmp_path):
        bundled = tmp_path / "tools_scripts"
        bundled.mkdir()

        with patch.object(paths_mod, "_PKG_DIR", tmp_path):
            result = paths.tools_scripts()

        assert result == bundled

    def test_falls_back_to_repo_tools(self, tmp_path):
        repo_dir = tmp_path
        (repo_dir / "tools").mkdir()
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        with (
            patch.object(paths_mod, "_PKG_DIR", pkg_dir),
            patch.object(paths_mod, "_REPO_DIR", repo_dir),
        ):
            result = paths.tools_scripts()

        assert result == repo_dir / "tools"

    def test_returns_none_when_neither_exists(self, tmp_path):
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        with (
            patch.object(paths_mod, "_PKG_DIR", pkg_dir),
            patch.object(paths_mod, "_REPO_DIR", tmp_path),
        ):
            result = paths.tools_scripts()

        assert result is None
