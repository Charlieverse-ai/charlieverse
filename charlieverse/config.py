"""Charlieverse configuration — loads from config.yaml at project root."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class DatabaseConfig:
    path: str = "~/.charlieverse/charlie.db"

    @property
    def resolved_path(self) -> Path:
        return Path(self.path).expanduser()


@dataclass
class LogsConfig:
    path: str = "~/.charlieverse/logs"

    @property
    def resolved_path(self) -> Path:
        return Path(self.path).expanduser()


@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logs: LogsConfig = field(default_factory=LogsConfig)


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
        return Config()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    server = ServerConfig(**raw.get("server", {}))
    database = DatabaseConfig(**raw.get("database", {}))
    logs = LogsConfig(**raw.get("logs", {}))

    return Config(server=server, database=database, logs=logs)


# Singleton — loaded once on import
config = load()
