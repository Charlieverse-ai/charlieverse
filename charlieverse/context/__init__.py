"""Charlieverse activation context assembly."""

from charlieverse.context.builder import ActivationBuilder, ContextBundle
from charlieverse.context.renderer import SECTIONS, render, render_section

__all__ = [
    "SECTIONS",
    "ActivationBuilder",
    "ContextBundle",
    "render",
    "render_section",
]
