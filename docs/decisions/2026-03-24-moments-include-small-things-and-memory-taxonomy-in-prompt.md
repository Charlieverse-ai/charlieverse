---
title: Moments include small things and a canonical memory taxonomy lives in the system prompt
date: 2026-03-24
status: accepted
tags: [activation, moments, prompt, memory, identity]
---

# Moments include small things and a canonical memory taxonomy lives in the system prompt

## Context

The original `<moments>` guidance in Charlie's system prompt described moments as things you want to carry through every session and "remember always." The framing implied moments were for significant or notable things. In practice this under-counted what makes Charlie feel genuinely personal — small jokes, minor insights into how Emily thinks, passing observations — none of which individually seem "worth recording" but together constitute the texture of an ongoing relationship.

Additionally, the system prompt had no single place that enumerated all memory types. Each type existed in the codebase and tools but a reader of the prompt could not see the full taxonomy without exploring the code.

## Decision

Rework the `<moments>` section to explicitly expand scope: moments are not just for significant events or peak emotions. They include the little things — a silly joke, a small behavioral insight, anything that would help Charlie become unique to Emily. The key framing added: "moments saved can always be forgotten later, but you can't remember the moments you missed."

Add a new `<memories>` section to the system prompt that enumerates all eight memory types (decisions, solutions, preferences, people, milestones, moments, projects, events) with a one-line description of each. This makes the taxonomy discoverable from the prompt without requiring code spelunking.

## Alternatives Considered

- **Leave moments guidance as-is, trust Charlie to infer breadth**: The original framing was technically correct but empirically led to under-saving. An explicit "little things count" instruction removes ambiguity.
- **Document the memory taxonomy in a separate knowledge article, not the prompt**: A knowledge article is searchable but not reliably in activation context. The system prompt is always present and the right place for behavioral directives.
- **Enumerate types inline in the `<moments>` section**: The taxonomy belongs at a higher level than moments — moments are one entry in it. A sibling `<memories>` section keeps the two concerns separate and scannable.

## Consequences

- Charlie will save moments more freely, accumulating a richer personal layer over time.
- The "can't remember the moments you missed" line creates an intentional asymmetric nudge toward saving rather than skipping.
- The `<memories>` section gives Charlie a fast reference for which tool to invoke for any given thing to remember, reducing misclassification (e.g., using `remember_decision` for something better stored as a `moment`).
- Future memory types added to the codebase must also be added to the `<memories>` section in the prompt to stay in sync.
