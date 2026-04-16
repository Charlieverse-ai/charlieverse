"""Package-relative path helpers.

Resolves bundled assets whether running from a dev checkout or an installed package (uvx/pip).
"""

from __future__ import annotations

from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_REPO_DIR = _PKG_DIR.parent


def _find(relative: str) -> Path | None:
    """Find a path relative to either the package dir or the repo root."""
    path = _REPO_DIR / relative
    if not path.exists():
        path = _REPO_DIR.parent / relative

    if path.exists():
        return path


def web_dist() -> Path | None:
    """Built web dashboard assets."""
    return _find("web/dist")


def integrations() -> Path | None:
    """Provider integration templates and scripts."""
    return _find("integrations")


def integration(provider: str) -> Path | None:
    """A specific provider's integration directory."""
    return _find(f"integrations/{provider}")


def prompts() -> Path | None:
    """Prompt files (Charlie.md, reminders, etc)."""
    return _find("prompts")


def tools_scripts() -> Path | None:
    """Standalone scripts (extract_conversations, etc)."""
    # Bundled as tools_scripts/ in wheel, tools/ in repo checkout
    bundled = _PKG_DIR / "tools_scripts"
    if bundled.exists():
        return bundled
    repo = _REPO_DIR / "tools"
    if repo.exists():
        return repo
    return None
