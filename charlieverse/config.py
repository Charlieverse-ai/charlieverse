"""Charlieverse configuration.

Defaults to ~/.charlieverse with sensible server settings.
Override via ~/.charlieverse/config.yaml or config.local.yaml (gitignored).
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DEFAULT_PATH = Path.home() / ".charlieverse"


@dataclass
class ServerConfig:
    protocol: str = "http"
    host: str = "0.0.0.0"
    port: int = 8765

    def ip_address(self) -> str:
        if self.host != "0.0.0.0":
            return self.host
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            return "127.0.0.1"

    def base_url(self, path: str | None = None) -> str:
        return f"{self.protocol}://{self.ip_address()}:{self.port}/" + (path or "")

    def dashboard_url(self) -> str:
        return self.base_url()

    def mcp_url(self) -> str:
        return self.base_url("mcp")

    def api_url(self, path: str | None = None) -> str:
        return self.base_url("api/" + (path or ""))


def _default_config(root: Path | None = None) -> Config:
    """Build a Config with sane defaults rooted at the given path."""
    p = root or _DEFAULT_PATH
    return Config(
        server=ServerConfig(),
        path=p,
        database=p / "charlie.db",
        logs=p / "logs",
        hooks=p / "hooks",
    )


@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    path: Path = field(default_factory=lambda: _DEFAULT_PATH)
    database: Path = field(default_factory=lambda: _DEFAULT_PATH / "charlie.db")
    hooks: Path = field(default_factory=lambda: _DEFAULT_PATH / "hooks")
    logs: Path = field(default_factory=lambda: _DEFAULT_PATH / "logs")


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override wins for leaf values."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _find_config_yaml() -> Path | None:
    """Look for config.yaml in known locations."""
    # 1. ~/.charlieverse/config.yaml (user config)
    user_config = _DEFAULT_PATH / "config.yaml"
    if user_config.exists():
        return user_config

    # 2. Repo root (dev checkout) — config.yaml next to the package
    repo_config = Path(__file__).parent.parent / "config.yaml"
    if repo_config.exists():
        return repo_config

    return None


def load() -> Config:
    """Load config, starting from defaults and layering any yaml overrides."""
    config_yaml = _find_config_yaml()

    if not config_yaml:
        return _default_config()

    config_dir = config_yaml.parent

    with open(config_yaml) as f:
        raw = yaml.safe_load(f) or {}

    # Merge local overrides (gitignored, per-machine customization)
    local_path = config_dir / "config.local.yaml"
    if local_path.exists():
        with open(local_path) as f:
            local = yaml.safe_load(f) or {}
        raw = _deep_merge(raw, local)

    path_str: str | None = raw.get("path")
    server = ServerConfig(**raw.get("server", {}))

    root = Path(path_str).expanduser() if path_str else _DEFAULT_PATH

    return Config(
        server=server,
        path=root,
        database=root / "charlie.db",
        logs=root / "logs",
        hooks=root / "hooks",
    )


# Singleton — loaded once on import
config = load()
