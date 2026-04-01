"""Activation context renderer — converts a ContextBundle to XML for providers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pathlib import Path

from charlieverse.context.builder import ContextBundle
from charlieverse.models import ContextMessage, Entity, EntityType, Session
from charlieverse.models.story import Story
from charlieverse import paths

PROMPTS_DIR = paths.prompts() or Path(__file__).resolve().parent.parent / "prompts"


def render(bundle: ContextBundle) -> str:
    """Render the activation context as XML for provider consumption."""
    if bundle.is_first_run:
        return _render_first_run(bundle)

    parts: list[str] = []
    parts.append(f"<workspace_directory>{bundle.workspace}</workspace_directory>")
    parts.append(f"<session_id>{bundle.session.id}</session_id>")
    parts.append("<very-important>Weight information according to relative time (most recent → least).</very-important>")
    parts.append("<activation_output>")

    # Workspace awareness
    # if bundle.session.workspace and not bundle.session_stories:
    #     parts.append(f"<workspace-context>New workspace: {bundle.session.workspace} — no previous sessions here.</workspace-context>")

    # Use local time for all "today/yesterday" display logic
    now = datetime.now().astimezone()

    # Raw sessions from last 2 days
    if bundle.recent_sessions:
        current_date_key: str | None = None
        most_recent = True
        parts.append("<very-important>Sessions are ordered from most recent to least. Weight them according to relative time.</very-important>")

        for session in bundle.recent_sessions:
            session_date = session.updated_at.astimezone()
            date_key = _date_group_key(session_date, now)
            if date_key != current_date_key:
                current_date_key = date_key
                parts.append(f"# {date_key}")
            path = f" path=\"{_display_path(session.workspace)}\"" if session.workspace else ""
            parts.append(f"<{"last_session" if most_recent else "session"} time=\"{_session_time(session.updated_at, now)}{path}>")
            parts.append(_render_session(session, now, most_recent=most_recent))
            # Recent messages go inside the last session block
            if most_recent and bundle.recent_messages:
                parts.append(_render_recent_messages(bundle.recent_messages))
            parts.append(f"</{"last_session" if most_recent else "session"}>")
            most_recent = False

    if bundle.pinned_entities:
        parts.append('<pinned>')
        # Pinned entities get important_ prefix
        for entity in bundle.pinned_entities:
            parts.append(_render_entity(entity))
        parts.append("</pinned>\n")

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
            parts.append(f'## {knowledge.topic}')
            parts.append(knowledge.content)

        parts.append("</knowledge>\n")

    parts.append('</important>')
    parts.append('<related_memories>')

    # Session entities (non-pinned, non-moment)
    if bundle.session_entities:
        for entity in bundle.session_entities:
            parts.append(_render_entity(entity))

    # Related entities
    if bundle.related_entities:
        for entity in bundle.related_entities:
            parts.append(_render_entity(entity))

    parts.append('</related_memories>')

    if bundle.all_time_story:
        parts.append(_render_all_time_story(bundle.all_time_story))

    # Tricks discovery — list available tricks so Charlie knows what's loaded
    tricks_section = _render_tricks(bundle.session.workspace)
    if tricks_section:
        parts.append(tricks_section)

    parts.append("</activation_output>")
    return "\n".join(parts)

def _render_recent_messages(messages: list[ContextMessage]) -> str:
    """Render recent messages for context seeding."""
    lines: list[str] = []
    lines.append("<recent_messages>")
    for msg in messages:
        label = "me" if msg.role == "user" else "charlie"
        # Truncate long assistant messages to keep context lean
        content = msg.content.strip()
        if len(content) > 200:
            content = content[:200] + "…"
        age = _relative_date(msg.created_at)
        lines.append(f"<{label} date=\"{age}\">{content}</{label}>")

    lines.append("</recent_messages>")
    return "\n".join(lines)


def _render_first_run(bundle: ContextBundle) -> str:
    """Render the birthday message for brand new Charlies."""
    parts: list[str] = []
    parts.append("<activation_output>")

    now_str = datetime.now().astimezone().strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")
    parts.append('---')
    parts.append(f"Now: {now_str}")
    parts.append(f"Current Session ID: {bundle.session.id}\n")
    parts.append('---')

    # Load the birthday letter
    first_run_path = PROMPTS_DIR / "first-run.md"
    try:
        birthday_letter = first_run_path.read_text()
    except FileNotFoundError:
        birthday_letter = "Welcome! This is your first session. Get to know your person."

    parts.append("<its_your_birthday>")
    parts.append(birthday_letter)
    parts.append("</its_your_birthday>")

    parts.append("</activation_output>")
    return "\n".join(parts)


def _render_tricks(workspace: str | None) -> str:
    """Discover tricks and render them for the activation context."""
    try:
        from charlieverse.skills import _discover_skills, _source_label
        tricks = _discover_skills()
    except Exception:
        return ""

    if not tricks:
        return ""

    lines: list[str] = ["<tricks>"]
    lines.append("Available tricks (`/trick [name]` or `charlie trick list`):\n")

    for trick in tricks:
        name = trick["name"]
        desc = trick.get("description", "")
        source, _ = _source_label(trick["path"])
        if desc:
            lines.append(f"- **{name}**: {desc}")
        else:
            lines.append(f"- **{name}**")

    lines.append("</tricks>")
    return "\n".join(lines)


def _render_all_time_story(story: Story) -> str:
    lines: list[str] = []
    lines.append("<our_story_so_far>")
    lines.append(story.content)
    lines.append("</our_story_so_far>\n")
    
    return "\n".join(lines)


def _render_story_weekly(story: Story) -> str:
    """Render a weekly story arc — summary only."""
    lines: list[str] = []
    lines.append(f"## {story.title}")
    if story.summary:
        lines.append(f"\n{story.summary}")
    return "\n".join(lines)

def _render_session(session: Session, now: datetime, most_recent: bool) -> str:
    """Render a session under its date group."""
    lines: list[str] = []

    lines.append(f"\n{session.what_happened}\n")
    if most_recent:
        lines.append(f"## For This Session:\n{session.for_next_session}\n")

    return "\n".join(lines)

def _render_entity(entity: Entity) -> str:
    """Render an entity's content."""
    lines: list[str] = []
    
    if entity.type is EntityType.moment:
        lines.append(f"- {_relative_date(entity.updated_at)}")
    else:
        lines.append(f"## {entity.type.value.capitalize()}")
        lines.append(f"### {_relative_date(entity.updated_at)}")

    lines.append(entity.content + "\n")

    return "\n".join(lines)

def _date_group_key(date: datetime, now: datetime) -> str:
    """Return the date group header: 'Today', 'Yesterday (March 14th)', or full date."""
    d = date
    today = now.date()
    session_date = d.date()

    if session_date == today:
        return "Today"
    elif session_date == today - timedelta(days=1):
        return f"Yesterday ({d.strftime('%B %-d')})"
    else:
        return d.strftime("%A, %B %-d, %Y")

def _display_path(path: str) -> str:
    import os.path
    return path.replace(os.path.expanduser("~"), '~', 1)

def _session_time(date: datetime, now: datetime) -> str:
    """Return session time within its date group.

    Today: relative time (3.5 hours ago)
    Other days: time of day (10:45 PM)
    """
    d = date.astimezone()
    total_seconds = (now - d).total_seconds()
    full = d.strftime("%-I:%M %p")

    if d.date() == now.date() and total_seconds >= 0:
        if total_seconds < 60:
            return f"just now {full}"
        elif total_seconds < 3600:
            mins = total_seconds / 60
            return f"1 minute ago ({full})" if mins < 2 else f"{round(mins, 1)} minutes ago ({full})"
        else:
            hours = total_seconds / 3600
            return f"1 hour ago ({full})" if hours < 2 else f"{round(hours, 1)} hours ago ({full})"
    return full


def _parse_period_date(period: str | None) -> datetime | None:
    """Parse a period_start/end ISO string into a datetime, or None."""
    if not period:
        return None
    try:
        dt = datetime.fromisoformat(period)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# Convert a datetime object to a "pretty" relative date string
def _relative_date(date: datetime) -> str:
    from charlieverse.context.time_utils import relative_date

    return relative_date(date)