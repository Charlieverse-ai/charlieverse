"""Activation context renderer — converts a ContextBundle to XML for providers."""

from __future__ import annotations

from datetime import datetime, timezone

from charlieverse.context.builder import ContextBundle
from charlieverse.models import Entity, EntityType, Knowledge, Session


def render(bundle: ContextBundle) -> str:
    """Render the activation context as XML for provider consumption."""
    parts: list[str] = []
    parts.append("<activation_output>")

    # Current datetime
    now = datetime.now(timezone.utc).strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
    parts.append(f"<current_datetime>{now}</current_datetime>")

    # Current session ID
    parts.append(f"<current_session_id>{bundle.session.id}</current_session_id>")

    # Recent sessions
    most_recent = True
    for session in bundle.recent_sessions:
        attrs = ' most_recent="true"' if most_recent else ""
        parts.append(f"<previous_session{attrs}>")
        parts.append(_render_session(session))
        parts.append("</previous_session>")
        most_recent = False

    # Pinned entities get important_ prefix
    for entity in bundle.pinned_entities:
        tag = f"important_{entity.type.value}"
        parts.append(f"<{tag}>")
        parts.append(_render_entity(entity))
        parts.append(f"</{tag}>")

    # Moments
    for entity in bundle.moments:
        parts.append("<moment>")
        parts.append(_render_entity(entity))
        parts.append("</moment>")

    # Session entities (non-pinned, non-moment)
    for entity in bundle.session_entities:
        tag = entity.type.value
        parts.append(f"<{tag}>")
        parts.append(_render_entity(entity))
        parts.append(f"</{tag}>")

    # Related entities
    for entity in bundle.related_entities:
        tag = entity.type.value
        parts.append(f"<{tag}>")
        parts.append(_render_entity(entity))
        parts.append(f"</{tag}>")

    # Pinned knowledge (expertise)
    for knowledge in bundle.pinned_knowledge:
        parts.append(f'<expertise topic="{_escape(knowledge.topic)}">')
        parts.append(knowledge.content)
        if knowledge.tags:
            parts.append(f"<tags>{','.join(knowledge.tags)}</tags>")
        parts.append("</expertise>")

    parts.append("</activation_output>")
    return "\n".join(parts)


def _render_session(session: Session) -> str:
    """Render a session's content."""
    lines: list[str] = []
    if session.what_happened:
        lines.append(f"<what_we_did>\n{session.what_happened}\n</what_we_did>")
    if session.for_next_session:
        lines.append(f"<for_next_session>\n{session.for_next_session}\n</for_next_session>")
    if session.tags:
        lines.append(f"<tags>{','.join(session.tags)}</tags>")
    return "\n".join(lines)


def _render_entity(entity: Entity) -> str:
    """Render an entity's content."""
    lines: list[str] = [entity.content]
    if entity.tags:
        lines.append(f"<tags>{','.join(entity.tags)}</tags>")
    return "\n".join(lines)


def _escape(text: str) -> str:
    """Escape XML special characters in attribute values."""
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
