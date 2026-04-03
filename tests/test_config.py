"""Tests for charlieverse/config.py — load, merge, and ServerConfig helpers."""

from __future__ import annotations

import textwrap
from unittest.mock import patch

from charlieverse.config import (
    Config,
    ServerConfig,
    _deep_merge,
    _default_config,
    load,
)

# ── ServerConfig ──────────────────────────────────────────────────────────────


class TestServerConfig:
    def test_ip_address_specific_host(self):
        sc = ServerConfig(host="192.168.1.1")
        assert sc.ip_address() == "192.168.1.1"

    def test_ip_address_wildcard_falls_back(self):
        sc = ServerConfig(host="0.0.0.0")
        # Should return some non-empty IP
        ip = sc.ip_address()
        assert ip
        assert "." in ip

    def test_ip_address_wildcard_gaierror_fallback(self):
        import socket

        sc = ServerConfig(host="0.0.0.0")
        with patch("socket.gethostbyname", side_effect=socket.gaierror):
            assert sc.ip_address() == "127.0.0.1"

    def test_base_url(self):
        sc = ServerConfig(protocol="http", host="127.0.0.1", port=8765)
        assert sc.base_url() == "http://127.0.0.1:8765/"

    def test_base_url_with_path(self):
        sc = ServerConfig(protocol="http", host="127.0.0.1", port=8765)
        assert sc.base_url("api/health") == "http://127.0.0.1:8765/api/health"

    def test_dashboard_url(self):
        sc = ServerConfig(protocol="http", host="127.0.0.1", port=8765)
        assert sc.dashboard_url() == sc.base_url()

    def test_mcp_url(self):
        sc = ServerConfig(protocol="http", host="127.0.0.1", port=8765)
        assert sc.mcp_url() == "http://127.0.0.1:8765/mcp"

    def test_api_url(self):
        sc = ServerConfig(protocol="http", host="127.0.0.1", port=8765)
        assert sc.api_url("entities") == "http://127.0.0.1:8765/api/entities"

    def test_api_url_no_path(self):
        sc = ServerConfig(protocol="http", host="127.0.0.1", port=8765)
        assert sc.api_url() == "http://127.0.0.1:8765/api/"


# ── _deep_merge ───────────────────────────────────────────────────────────────


class TestDeepMerge:
    def test_flat_override(self):
        result = _deep_merge({"a": 1, "b": 2}, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_nested_merge(self):
        base = {"server": {"host": "127.0.0.1", "port": 8765}}
        override = {"server": {"port": 9000}}
        result = _deep_merge(base, override)
        assert result == {"server": {"host": "127.0.0.1", "port": 9000}}

    def test_override_wins_on_type_conflict(self):
        result = _deep_merge({"a": {"nested": 1}}, {"a": "string"})
        assert result == {"a": "string"}

    def test_new_keys_added(self):
        result = _deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_base_not_mutated(self):
        base = {"a": 1}
        _deep_merge(base, {"b": 2})
        assert base == {"a": 1}


# ── _default_config ───────────────────────────────────────────────────────────


class TestDefaultConfig:
    def test_defaults_to_home_charlieverse(self, tmp_path):
        cfg = _default_config(tmp_path)
        assert cfg.path == tmp_path
        assert cfg.database == tmp_path / "charlie.db"
        assert cfg.logs == tmp_path / "logs"
        assert cfg.hooks == tmp_path / "hooks"

    def test_server_config_present(self, tmp_path):
        cfg = _default_config(tmp_path)
        assert isinstance(cfg.server, ServerConfig)


# ── load() ────────────────────────────────────────────────────────────────────


class TestLoad:
    def test_no_config_returns_defaults(self):
        with patch("charlieverse.config._find_config_yaml", return_value=None):
            cfg = load()
        assert isinstance(cfg, Config)
        assert cfg.database == cfg.path / "charlie.db"

    def test_config_yaml_sets_path(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"path: {tmp_path}\n")

        with patch("charlieverse.config._find_config_yaml", return_value=config_file):
            cfg = load()

        assert cfg.path == tmp_path
        assert cfg.database == tmp_path / "charlie.db"

    def test_config_yaml_sets_server_port(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            textwrap.dedent(f"""\
                path: {tmp_path}
                server:
                  port: 9999
            """)
        )

        with patch("charlieverse.config._find_config_yaml", return_value=config_file):
            cfg = load()

        assert cfg.server.port == 9999

    def test_local_yaml_overrides_base(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            textwrap.dedent(f"""\
                path: {tmp_path}
                server:
                  port: 8765
            """)
        )
        local_file = tmp_path / "config.local.yaml"
        local_file.write_text("server:\n  port: 7777\n")

        with patch("charlieverse.config._find_config_yaml", return_value=config_file):
            cfg = load()

        assert cfg.server.port == 7777

    def test_empty_yaml_uses_defaults(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        with patch("charlieverse.config._find_config_yaml", return_value=config_file):
            cfg = load()

        assert isinstance(cfg, Config)
        assert cfg.server.port == 8765
