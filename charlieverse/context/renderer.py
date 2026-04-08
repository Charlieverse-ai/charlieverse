"""Activation context renderer — converts a ContextBundle to XML for providers."""

from __future__ import annotations

import os.path
from datetime import timedelta
from pathlib import Path

from charlieverse.context.builder import ContextBundle
from charlieverse.helpers import paths
from charlieverse.helpers.time_utils import relative_date
from charlieverse.memory.entities import Entity, EntityType
from charlieverse.memory.messages import Message
from charlieverse.memory.sessions import Session
from charlieverse.types.dates import LocalDatetime, UTCDatetime, from_iso_or_none, local_now, to_local

PROMPTS_DIR = paths.prompts() or Path(__file__).resolve().parent.parent / "prompts"


def render(bundle: ContextBundle) -> str:
    """Render the activation context as XML for provider consumption."""
    renderer = Renderer()
    renderer.append(f"<session_id>{bundle.session.id}</session_id>")
    renderer.append("<very-important>Weight information according to relative time (most recent → least).</very-important>")

    if bundle.is_first_run:
        _render_first_run(bundle, renderer)
    else:
        _render_context(bundle, renderer)

    return renderer.render()


def _render_context(bundle: ContextBundle, renderer: Renderer):
    # Use local time for all "today/yesterday" display logic
    now = local_now()
    # Raw sessions from last 2 days
    if bundle.recent_sessions:
        current_date_key: str | None = None
        most_recent = True
        renderer.append("<sessions>")

        for session in bundle.recent_sessions:
            session_date = to_local(session.updated_at)
            date_key = _date_group_key(session_date, now)
            if date_key != current_date_key:
                current_date_key = date_key
                # renderer.append(f"# {date_key}")

            workspace = _display_path(session.workspace)
            path = f' path="{workspace}"' if workspace else ""
            most_recent_attr = ' most_recent="true"' if most_recent else ""

            tag = "session"

            renderer.append(f'<{tag} time="{relative_date(session.updated_at)}"{path}{most_recent_attr}>')
            renderer.append(_render_session(session, now, most_recent=most_recent))
            renderer.append(f"</{tag}>")
            most_recent = False
        renderer.append("</sessions>")

    renderer.append_entities(bundle.pinned_entities)
    renderer.append_entities(bundle.moments)

    # Pinned knowledge (expertise)
    if bundle.pinned_knowledge:
        renderer.append("<knowledge>")
        for knowledge in bundle.pinned_knowledge:
            renderer.append(f"## {knowledge.topic}")
            renderer.append(knowledge.content)

        renderer.append("</knowledge>")

    if bundle.session_entities or bundle.related_entities:
        renderer.append("<related_memories>")
        renderer.append_entities([*bundle.session_entities, *bundle.related_entities])
        renderer.append("</related_memories>")

    if bundle.all_time_story:
        renderer.append(bundle.all_time_story.content, "our_story_so_far")


def _render_recent_messages(messages: list[Message]) -> str:
    """Render recent messages for context seeding."""
    lines: list[str] = []
    lines.append("<recent_messages>")
    for msg in messages:
        label = "me" if msg.role == "user" else "charlie"
        # Truncate long assistant messages to keep context lean
        content = msg.content.strip()
        if len(content) > 200:
            content = content[:200] + "…"
        age = relative_date(msg.created_at)
        lines.append(f'<{label} date="{age}">{content}</{label}>')

    lines.append("</recent_messages>")
    return "\n".join(lines)


def _render_first_run(bundle: ContextBundle, renderer: Renderer):
    """Render the birthday message for brand new Charlies."""
    # Load the birthday letter
    first_run_path = PROMPTS_DIR / "first-run.md"
    try:
        birthday_letter = first_run_path.read_text()
    except FileNotFoundError:
        birthday_letter = "Welcome! This is your first session. Get to know your person."

    renderer.append("<its_your_birthday>")
    renderer.append(birthday_letter)
    renderer.append("</its_your_birthday>")


def _render_tricks(workspace: str | None) -> str:
    """Discover tricks and render them for the activation context."""
    try:
        from charlieverse.helpers.skills import _discover_skills

        tricks = _discover_skills()
    except Exception:
        return ""

    if not tricks:
        return ""

    lines: list[str] = ["<tricks>"]
    lines.append("Available tricks (`/trick [name]` or `charlie trick list`):\n")

    for trick in tricks:
        name = trick.get("name")
        desc = trick.get("description")
        lines.append(f"- {name}{f': {desc}' if desc else ''}")

    lines.append("</tricks>")
    return "\n".join(lines)


def _render_session(session: Session, now: LocalDatetime, most_recent: bool) -> str:
    """Render a session under its date group."""
    lines: list[str] = []

    lines.append(f"What we did:\n{session.what_happened}\n")
    # if most_recent:
    lines.append(f"For Next:\n{session.for_next_session}")

    return "\n".join(lines)


def _render_entity(entity: Entity, renderer: Renderer):
    """Render an entity's content."""
    important = entity.pinned or entity.type == EntityType.moment

    tag = f"important-{entity.type}" if important else entity.type
    attrs = f'date="{relative_date(entity.updated_at)}">'

    renderer.append(entity.content, tag=tag, attrs=attrs)


def _date_group_key(date: LocalDatetime, now: LocalDatetime) -> str:
    """Return the date group header: 'Today', 'Yesterday (March 14th)', or full date."""
    today = now.date()
    session_date = date.date()

    if session_date == today:
        return "Today"
    elif session_date == today - timedelta(days=1):
        return f"Yesterday ({date.strftime('%B %-d')})"
    else:
        return date.strftime("%A, %B %-d, %Y")


def _display_path(path: str | None) -> str | None:
    if not path:
        return None
    path = path.strip()
    path.replace(os.path.expanduser("~"), "~", 1)


def _session_time(date: UTCDatetime, now: LocalDatetime) -> str:
    """Return session time within its date group.

    Today: relative time (3.5 hours ago)
    Other days: time of day (10:45 PM)
    """
    local = to_local(date)
    total_seconds = (now - local).total_seconds()
    full = local.strftime("%-I:%M %p")

    if local.date() == now.date() and total_seconds >= 0:
        if total_seconds < 60:
            return f"just now {full}"
        elif total_seconds < 3600:
            mins = total_seconds / 60
            return f"1 minute ago ({full})" if mins < 2 else f"{round(mins, 1)} minutes ago ({full})"
        else:
            hours = total_seconds / 3600
            return f"1 hour ago ({full})" if hours < 2 else f"{round(hours, 1)} hours ago ({full})"
    return full


def _parse_period_date(period: str | None) -> UTCDatetime | None:
    """Parse a period_start/end ISO string into a UTC instant, or None."""
    try:
        return from_iso_or_none(period)
    except (ValueError, TypeError):
        return None


class Renderer:
    _parts: list[str]

    def __init__(self):
        self._parts = []

    def append(self, line: str | None, tag: str | None = None, attrs: str | None = None):
        if not line:
            return

        if tag:
            line = f"<{tag}{f' {attrs}' if attrs else ''}>\n{line}\n</{tag}>"

        self._parts.append(line)

    def render(self) -> str:
        return "\n".join(self._parts)

    def append_entities(self, entities: list[Entity] | None):
        if not entities:
            return
        for entity in entities:
            self.append_entity(entity)

    def append_entity(self, entity: Entity):
        important = entity.pinned or entity.type == EntityType.moment

        tag = f"important-{entity.type}" if important else entity.type
        attrs = f'date="{relative_date(entity.updated_at)}"'

        self.append(entity.content, tag=tag, attrs=attrs)
