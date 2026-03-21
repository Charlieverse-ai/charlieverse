"""Skill discovery — find and parse SKILL.md files across all provider directories."""

from __future__ import annotations

import re
from pathlib import Path

from charlieverse.config import config


def _parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from a SKILL.md file."""
    import yaml

    text = path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    try:
        parsed = yaml.safe_load(match.group(1))
        if isinstance(parsed, dict):
            return {k: str(v) for k, v in parsed.items() if v is not None}
    except Exception:
        pass
    return {}


def _skill_dirs() -> list[Path]:
    """Return all directories to scan for skills, in priority order.

    Scans Charlieverse paths first, then standard Agent Skills paths
    that other providers may have installed to. First match wins by name.
    """
    dirs: list[Path] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        resolved = str(p.resolve())
        if resolved not in seen and p.is_dir():
            seen.add(resolved)
            dirs.append(p)

    # 1. Charlieverse tricks (highest priority)
    _add(config.path / "tricks")

    # 2. Project-local tricks (.charlie/tricks/ in cwd)
    cwd = Path.cwd()
    _add(cwd / ".charlie" / "tricks")

    # 3. Cross-platform standard paths (.agents/skills/)
    home = Path.home()
    _add(home / ".agents" / "skills")

    # Provider-specific user-level paths (auto-discover)
    # Excluding ~/.claude/skills/ — those are managed by the install script
    # and already show up in the provider's own /skills menu.
    for provider_dir in [
        home / ".copilot" / "skills",
        home / ".cursor" / "skills",
        home / ".codex" / "skills",
        home / ".codeium" / "windsurf" / "skills",
        home / ".gemini" / "skills",
    ]:
        _add(provider_dir)

    # 5. Project-level paths (cwd-relative)
    for project_dir in [
        cwd / ".agents" / "skills",
        cwd / ".claude" / "skills",
        cwd / ".github" / "skills",
        cwd / ".cursor" / "skills",
    ]:
        _add(project_dir)

    # Integration-specific skills (Claude, Copilot, etc.) are excluded —
    # those are registered directly with their provider and show up
    # in the provider's own skill/slash-command system.

    return dirs


def _discover_skills() -> list[dict]:
    """Find all available skills across all directories."""
    seen: set[str] = set()
    skills: list[dict] = []

    for parent in _skill_dirs():
        for skill_dir in sorted(parent.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            fm = _parse_frontmatter(skill_md)
            name = fm.get("name", skill_dir.name)

            # First match wins (user-installed overrides bundled)
            if name in seen:
                continue
            seen.add(name)

            skills.append({
                "name": name,
                "description": fm.get("description", ""),
                "path": str(skill_md),
            })

    return skills


def _find_skill(name: str) -> Path | None:
    """Find a skill by name. First match wins."""
    for parent in _skill_dirs():
        skill_md = parent / name / "SKILL.md"
        if skill_md.exists():
            return skill_md
    return None


def _source_label(path_str: str) -> tuple[str, str]:
    """Return (source, style) for a skill path."""
    if str(config.path) in path_str:
        return "user", "green"
    elif "/integrations/" in path_str:
        return "integration", "yellow"
    elif "/prompts/skills/" in path_str:
        return "bundled", "cyan"
    # Provider-specific paths
    elif "/.claude/" in path_str:
        return "claude", "magenta"
    elif "/.copilot/" in path_str:
        return "copilot", "blue"
    elif "/.cursor/" in path_str:
        return "cursor", "blue"
    elif "/.codex/" in path_str:
        return "codex", "blue"
    elif "/.codeium/" in path_str or "/windsurf/" in path_str:
        return "windsurf", "blue"
    elif "/.gemini/" in path_str:
        return "gemini", "blue"
    elif "/.agents/" in path_str:
        return "shared", "dim"
    elif "/.charlie/" in path_str:
        return "project", "green"
    elif "/.github/" in path_str:
        return "github", "dim"
    return "other", "dim"
