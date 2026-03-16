"""Activation context renderer — converts a ContextBundle to XML for providers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from charlieverse.context.builder import ContextBundle
from charlieverse.models import Entity, EntityType, Knowledge, Session


def render(bundle: ContextBundle) -> str:
    """Render the activation context as XML for provider consumption."""
    parts: list[str] = []
    parts.append("<activation_output>")

    # Current datetime
    parts.append('---')
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
    parts.append(f"Now: {now}")
    parts.append(f"Current Session ID: {bundle.session.id}\n")
    parts.append('---')

    parts.append('<past_sessions>')
    # Recent sessions grouped by date — skip empty ones
    now = datetime.now(timezone.utc)
    valid_sessions = [
        s for s in bundle.recent_sessions
        if s.what_happened or s.for_next_session
    ]
    most_recent = True
    current_date_key: str | None = None
    for session in valid_sessions:
        date_key = _date_group_key(session.updated_at, now)
        if date_key != current_date_key:
            current_date_key = date_key
            parts.append(f"# {date_key}")
        parts.append(_render_session(session, now, most_recent=most_recent))
        most_recent = False

    parts.append('</past_sessions>')

    parts.append('<important>')
    if bundle.pinned_entities:
        parts.append('<memories>')
        # Pinned entities get important_ prefix
        for entity in bundle.pinned_entities:
            parts.append(_render_entity(entity))
        parts.append("</memories>\n")

    # Moments
    if bundle.moments:
        parts.append('<moments>')
        for entity in bundle.moments:
            parts.append(_render_entity(entity))
        parts.append("</moments>\n")

    # Pinned knowledge (expertise)
    if bundle.pinned_knowledge:
        parts.append('<knowledge>')
    
        for knowledge in bundle.pinned_knowledge:
            parts.append(f'## Article: {knowledge.topic}')
            parts.append(knowledge.content)
            if knowledge.tags:
                parts.append(f"- Tags: {','.join(knowledge.tags)}")

        parts.append("</knowledge>\n")

    parts.append('</important>')

    parts.append('<related_session_memories>')

    # Session entities (non-pinned, non-moment)
    if bundle.session_entities:
        parts.append('<created_recently>')
        for entity in bundle.session_entities:
            parts.append(_render_entity(entity))
        parts.append('</created_recently>')

    # Related entities
    if bundle.related_entities:
        parts.append('<semantic_relevance>')
        for entity in bundle.related_entities:
            parts.append(_render_entity(entity))
        parts.append('</semantic_relevance>')

    parts.append('</related_session_memories>')

    parts.append("</activation_output>")
    return "\n".join(parts)


def _render_session(session: Session, now: datetime, most_recent: bool) -> str:
    """Render a session under its date group."""
    lines: list[str] = []

    lines.append(f"## {_session_time(session.updated_at, now)}")

    if session.tags or session.workspace:
        lines.append('---')
        if session.workspace:
            lines.append(f"Workspace: {session.workspace}")
        if session.tags:
            lines.append(f"Tags: {','.join(session.tags)}")
        lines.append('---')

    lines.append(f"\n{session.what_happened}")
    if most_recent:
        lines.append(f"\n## For This Session:\n{session.for_next_session}")

    return "\n".join(lines)

def _render_entity(entity: Entity) -> str:
    """Render an entity's content."""
    lines: list[str] = []
    
    if entity.type is EntityType.moment:
        lines.append(f"## {_relative_date(entity.updated_at)}")
    else:
        lines.append(f"## {entity.type.value.capitalize()}: {_relative_date(entity.updated_at)}")
    
    if entity.tags:
        lines.append(f"### Tags: {','.join(entity.tags)}")

    lines.append(entity.content + "\n")

    return "\n".join(lines)

def _date_group_key(date: datetime, now: datetime) -> str:
    """Return the date group header: 'Today', 'Yesterday (March 14th)', or full date."""
    d = date.replace(tzinfo=timezone.utc)
    today = now.date()
    session_date = d.date()

    if session_date == today:
        return "Today"
    elif session_date == today - timedelta(days=1):
        return f"Yesterday ({d.strftime('%B %-d')})"
    else:
        return d.strftime("%A, %B %-d, %Y")


def _session_time(date: datetime, now: datetime) -> str:
    """Return session time within its date group.

    Today: relative time (3.5 hours ago)
    Other days: time of day (10:45 PM)
    """
    d = date.replace(tzinfo=timezone.utc)
    total_seconds = (now - d).total_seconds()

    if d.date() == now.date() and total_seconds >= 0:
        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:
            mins = total_seconds / 60
            return "1 minute ago" if mins < 2 else f"{round(mins, 1)} minutes ago"
        else:
            hours = total_seconds / 3600
            return "1 hour ago" if hours < 2 else f"{round(hours, 1)} hours ago"
    return d.strftime("%-I:%M %p")


# Convert a datetime object to a "pretty" relative date string
def _relative_date(date: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = now - date.replace(tzinfo=timezone.utc)
    total_seconds = diff.total_seconds()

    if total_seconds < 0:
        return date.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
    elif total_seconds <= 1:
        return 'just now'
    elif total_seconds < 60:
        return '{} seconds ago'.format(int(total_seconds))
    elif total_seconds < 3600:
        mins = total_seconds / 60
        return '1 minute ago' if mins < 2 else '{} minutes ago'.format(round(mins, 2))
    elif total_seconds < 86400:
        hours = total_seconds / 3600
        return '1 hour ago' if hours < 2 else '{} hours ago'.format(round(hours, 2))
    elif total_seconds < 172800:
        return '1 day ago'
    elif total_seconds < 604800:
        return '{} days ago'.format(int(total_seconds / 86400))
    else:
        return date.strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")