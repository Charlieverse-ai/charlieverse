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

def _find_config() -> Path | None:
    """Walk up from this file to find config.yaml at the project root."""
    current = Path(__file__).parent.parent
    config_path = current / "config.yaml"
    if config_path.exists():
        return config_path
    return None


def load() -> Config:
    """Load configuration from config.yaml, falling back to defaults."""
    config_path = _find_config()
    if not config_path:
        # TODO Error?
        return Config()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    path: str | None = raw.get("path")
    server = ServerConfig(**raw.get("server", {}))

    if not path:
        # TODO Error?
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
