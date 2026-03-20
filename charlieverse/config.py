"""Charlieverse configuration — loads from config.yaml at project root."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
import socket

@dataclass
class ServerConfig:
    protocol: str = "http"
    host: str = "127.0.0.1"
    port: int = 8765

    def ip_address(self) -> str:
        if not self.host == "0.0.0.0":
            return self.host
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        return ip_address

    def base_url(self, path: str | None = None) -> str:
        return f"{self.protocol}://{self.ip_address()}:{self.port}/" + (path or "")
    
    def dashboard_url(self) -> str:
        return self.base_url()
    
    def mcp_url(self) -> str:
        return self.base_url("mcp")
    
    def api_url(self, path: str | None = None) -> str:
        return self.base_url("api/" + (path or ""))

@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    path: Path = field(default_factory=Path)
    database: Path = field(default_factory=Path)
    hooks: Path = field(default_factory=Path)
    logs: Path = field(default_factory=Path)

def _find_config_dir() -> Path | None:
    """Find the project root containing config.yaml."""
    current = Path(__file__).parent.parent
    if (current / "config.yaml").exists():
        return current
    return None


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override wins for leaf values."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load() -> Config:
    """Load config.yaml, then merge config.local.yaml on top (if it exists)."""
    config_dir = _find_config_dir()
    if not config_dir:
        return Config()

    with open(config_dir / "config.yaml") as f:
        raw = yaml.safe_load(f) or {}

    # Merge local overrides (gitignored, per-machine customization)
    local_path = config_dir / "config.local.yaml"
    if local_path.exists():
        with open(local_path) as f:
            local = yaml.safe_load(f) or {}
        raw = _deep_merge(raw, local)

    path: str | None = raw.get("path")
    server = ServerConfig(**raw.get("server", {}))

    if not path:
        return Config()

    full_path = Path(path).expanduser()

    return Config(
        server=server,
        path=full_path,
        database=full_path / "charlie.db",
        logs=full_path / "logs",
        hooks=full_path / "hooks"
    )


# Singleton — loaded once on import
config = load()
