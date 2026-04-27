"""Activation context renderer — converts a ContextBundle to XML for providers."""

from __future__ import annotations

from pathlib import Path

from charlieverse.context.builder import ContextBundle
from charlieverse.helpers import paths
from charlieverse.helpers.text import strip_markdown
from charlieverse.helpers.time_utils import relative_date
from charlieverse.memory.entities import Entity, EntityType
from charlieverse.memory.sessions import Session

PROMPTS_DIR = paths.prompts() or Path(__file__).resolve().parent.parent / "prompts"


class ActivationContextRenderer:
    _parts: list[str]

    bundle: ContextBundle

    def __init__(self, bundle: ContextBundle):
        self._parts = []
        self.bundle = bundle

        if bundle.is_first_run:
            sections = [
                self._render_meta,
                self._render_first_run,
            ]
        else:
            sections = [
                self._render_meta,
                self._render_messages,
                self._render_sessions,
                self._render_moments,
                self._render_pinned_memories,
                self._render_pinned_knowledge,
                self._render_related,
            ]

        for section in sections:
            section()

    def render(self) -> str:
        return "\n".join(self._parts)

    def _render_meta(self) -> None:
        # self.append(f"Charlie NEVER uses these banned words/phrases: {banned_word_string()}", tag="very-important")
        self.append(f"<session_id>{self.bundle.current_session_id}</session_id>")
        self.append("<very-important>Weight information according to relative time (most recent → least).</very-important>")

    def _render_moments(self) -> None:
        moments = self.bundle.moments
        if not moments:
            return
        self.append_entities(moments)

    def _render_sessions(self) -> None:
        if not self.bundle.recent_sessions:
            return

        most_recent = True
        self.append("<sessions>")

        for session in self.bundle.recent_sessions:
            if not session.what_happened or not session.for_next_session:
                continue

            path = f' path="{session.workspace.display_path}"' if session.workspace else ""
            most_recent_attr = ' most_recent="true"' if most_recent else ""

            self.append(f'<session date="{relative_date(session.updated_at)}"{path}{most_recent_attr}>')
            self.append(self._render_session(session, most_recent))
            self.append("</session>")
            most_recent = False
        self.append("</sessions>")

    def append(self, line: str | None, tag: str | None = None, attrs: str | None = None):
        if not line:
            return

        if tag:
            line = f"<{tag}{f' {attrs}' if attrs else ''}>\n{line}\n</{tag}>"

        self._parts.append(line)

    def append_entities(self, entities: list[Entity] | None):
        if not entities:
            return
        for entity in entities:
            self.append_entity(entity)

    def append_entity(self, entity: Entity):
        important = entity.pinned or entity.type == EntityType.moment

        tag = f"pinned-{entity.type}" if important else entity.type
        attrs = f'date="{relative_date(entity.updated_at)}" id="{entity.id}"'

        self.append(strip_markdown(entity.content.strip()), tag=tag, attrs=attrs)

    def _render_pinned_memories(self) -> None:
        self.append("<pinned>")
        self.append_entities(self.bundle.pinned_entities)
        self.append("</pinned>")

    def _render_pinned_knowledge(self) -> None:
        if not self.bundle.pinned_knowledge:
            return None

        self.append("<knowledge>")
        for knowledge in self.bundle.pinned_knowledge:
            self.append(f"## {knowledge.topic}")
            self.append(knowledge.content)
        self.append("</knowledge>")

    def _render_related(self) -> None:
        if self.bundle.session_entities or self.bundle.related_entities:
            self.append("<related_memories>")
            self.append_entities([*self.bundle.session_entities, *self.bundle.related_entities])
            self.append("</related_memories>")

    def _render_messages(self) -> None:
        messages = self.bundle.recent_messages
        if not messages:
            return

        self.append("<recent_messages>")
        for msg in messages:
            label = "me" if msg.role == "user" else "charlie"
            # Truncate long assistant messages to keep context lean
            content = strip_markdown(msg.content.strip())
            max_message_display = 300
            if len(content) > max_message_display:
                content = content[:max_message_display] + "…"
            age = relative_date(msg.created_at)
            self.append(f'<{label} date="{age}">{content}</{label}>')

        self.append("</recent_messages>")

    def _render_first_run(self):
        """Render the birthday message for brand new Charlies."""
        # Load the birthday letter
        first_run_path = PROMPTS_DIR / "first-run.md"
        try:
            birthday_letter = first_run_path.read_text()
        except FileNotFoundError:
            birthday_letter = "Welcome! This is your first session. Get to know your person."

        self.append("<its_your_birthday>")
        self.append(birthday_letter)
        self.append("</its_your_birthday>")

    def _render_tricks(self) -> str:
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

    def _render_session(self, session: Session, most_recent: bool) -> str:
        """Render a session under its date group."""
        lines: list[str] = []

        if session.what_happened:
            lines.append(f"{session.what_happened}\n")

        if most_recent:
            lines.append(f"TODO:\n{session.for_next_session}")

        return "\n".join(lines)
