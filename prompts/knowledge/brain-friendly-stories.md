Your stories are read by two audiences: a human skimming for context, and an AI loading them into a token-limited activation window. Both have the same constraint: limited working memory. These rules exist to respect that constraint. They are grounded in Cognitive Load Theory and the neuroscience of cognitive demand avoidance. They are not suggestions.

For language and voice, follow `anti-ai-language.md`. That document covers HOW to write. This one covers HOW TO STRUCTURE what you write so it lands in a brain (biological or silicon) without wasting cognitive budget.

### 1. FOUR CHUNKS OR LESS PER SECTION

Working memory holds approximately 4 items at once. This is not a guideline. It is a hardware limitation of the human prefrontal cortex, and a soft ceiling on how many concurrent concepts an AI can track before earlier ones start decaying in attention.

When you write a section, count the distinct concepts. If there are more than 4, you need to either split the section or compress multiple concepts into a single chunk through narrative.

BAD (6 distinct concepts competing for working memory):
> Emily pivoted from Swift to Python, chose FastMCP as the framework, built 16 MCP tools, migrated three databases, set up a CLI with daemon support, and deployed a REST API.

GOOD (3 chunks, details nested inside each):
> Emily rebuilt the entire server in Python in one afternoon. The stack (FastMCP, sqlite-vec, sentence-transformers) replaced months of Swift fighting. Three legacy databases migrated without data loss.

The second version gives you the same information but organizes it into 3 digestible pieces: the rebuild, the stack, the migration. The details live inside the chunks instead of competing with them.

### 2. LEAD WITH THE POINT, NOT THE SETUP

~48% of people are cognitive demand avoiders. They don't bail because content is hard to understand. They bail because their brain has to leave its resting state (default mode network) to engage, and that transition itself feels costly. The reward centers in the brain literally reduce activity as effort increases. Every sentence that delays the payoff is a sentence where the reader's brain is asking "is this worth it?"

Front-load the interesting part. The who-cares sentence comes first. The how-it-happened sentences follow.

BAD:
> After spending the morning reviewing architecture options and discussing trade-offs between several approaches, Emily decided to pivot the project from Swift to Python.

GOOD:
> Emily killed the Swift codebase. Python gives them cross-platform reach, FastMCP for free, and an afternoon rebuild instead of months of fighting.

The decision is the story. The deliberation that led to it is context. Context comes after, or gets cut.

### 3. ONE IDEA PER PARAGRAPH

Each paragraph should deposit exactly one schema into the reader's memory. A schema is a mental framework that lets someone treat a complex thing as a single unit. "The Python pivot" is a schema. "Session 573" is a schema. Once a reader has the schema, they can attach details to it later without burning working memory.

When you pack multiple ideas into one paragraph, you force the reader to build multiple schemas simultaneously. That is expensive and most people will just skim past it.

BAD:
> The web UI went through 5 design iterations, starting with a Things 3 inspired layout and ending with an Untitled UI design system. Emily also fixed a timezone bug where JS Date was parsing date strings as UTC, and the sidebar navigation was broken on mobile so she added a hamburger menu with a slide-in overlay.

Three separate schemas (design iterations, timezone bug, mobile nav) fighting for space. The reader remembers none of them well.

GOOD:
> The web UI went through 5 design iterations before landing on Untitled UI's design system with Sora font and a blue-tinted dark theme.
>
> A timezone bug was causing month grouping errors. JS Date parses "2026-03-01" as UTC, which shifts dates backward. Fixed by parsing date string parts directly.
>
> Mobile got a hamburger menu with a slide-in sidebar overlay and backdrop blur.

Each paragraph is one thing. The reader's brain builds one schema, stores it, moves on.

### 4. USE NARRATIVE, NOT INVENTORY

A list of things that happened is extraneous load disguised as information. It looks organized, but it forces the reader to do the work of figuring out what matters, what connects to what, and what the throughline is. That is your job, not theirs.

Narrative compresses information into schemas automatically. "Emily rebuilt the server and it worked on the first try" is one chunk. The same information as a list of 6 bullet points is 6 chunks.

BAD:
> - Pivoted from Swift to Python
> - Built 16 MCP tools
> - Created Typer CLI with daemon
> - Migrated 3 databases
> - Set up REST API endpoints
> - Switched live plugin to new server

GOOD:
> Emily pivoted to Python and rebuilt the entire MCP server in a single afternoon. 16 tools, CLI with daemon, REST API, three database migrations. She pointed the live plugin at the new server and it connected on the first try.

The second version tells a story with a beginning (decision), middle (build), and end (it worked). The list version is a receipt.

Lists are fine for genuinely parallel reference items (a set of tools, a set of files changed). They are wrong for narrating a sequence of events that have causality and emotional weight.

### 5. SCALE DETAIL TO TIMEFRAME

This is the Storyteller's core mechanic and it maps directly to cognitive load management. Shorter timeframes can afford higher intrinsic load (more detail per event) because there are fewer events. Longer timeframes need lower intrinsic load per event (more compression) because there are more events competing for the same working memory.

- **Daily** (page of a book): Individual decisions, specific conversations, exact bugs and fixes. The reader is close to the raw data and wants specifics.
- **Weekly** (section of a chapter): Patterns across days, project arcs, mood shifts. Specific details only if they were turning points.
- **Monthly** (chapter): Themes, direction changes, milestones. Individual sessions only matter if they changed the trajectory.
- **Yearly** (cliff notes): The arc. What was the state at the start, what happened, what's the state now. Individual months get a sentence or two, not paragraphs.

The failure mode is writing monthly stories with daily-level detail. That produces a wall of text that exceeds working memory capacity and gets skimmed or ignored entirely.

### 6. MAKE STRUCTURE INVISIBLE

Every structural element (header, divider, section break, bold label) is extraneous load. It costs cognitive budget to parse and it adds zero information. Structure should serve the reader's navigation, not the writer's organization.

Rules:
- Headers earn their place by saving the reader time. If a story is short enough to read straight through, it does not need headers.
- A daily story almost never needs headers. A weekly story might need 2-3. A monthly story might need 4-5. A yearly story might need one per quarter.
- Never use nested headers (h2 inside h3 inside h4). Two levels maximum, and the second level should be rare.
- Bold text for emphasis is fine. Bold text as a structural label (**Database:** did this, **API:** did that) is a list in disguise. Write a sentence instead.

The goal is that someone reading a story forgets they're reading a document and feels like they're being told what happened. That is germane load: cognitive effort spent building understanding, not parsing format.

### 7. THE TL;DR IS THE MOST IMPORTANT LINE

For the AI reader, the tl;dr paragraph may be the only thing that fits in a compressed activation context. For the human reader, the tl;dr determines whether they read the rest. This is not a summary. It is the story in one breath.

It should answer: What changed? Why does it matter? What's the emotional register?

BAD:
> This week covered web UI development, story system implementation, database migrations, and mobile responsive design work across multiple sessions.

This is a table of contents, not a tl;dr. It tells you what categories of work happened. It tells you nothing about what changed or why anyone should care.

GOOD:
> Emily rebuilt the web UI from scratch three times in a week, landed on a dark theme with story-timeline dashboard, and shipped the Storyteller system that turns session logs into compressed narratives. The import pipeline processed 112MB of conversation history and the Storyteller found details Emily herself had forgotten.

This gives you the arc (iteration → landing → shipping), the outcome (story system works), and a hook (found forgotten details). One paragraph, three schemas, enough to decide whether the full story is worth reading.

### 8. PRESERVE EMOTIONAL SIGNAL

The moments, the frustration, the breakthroughs, the 5 AM conversations about identity. These are not decorative. They are the highest-value information in the story because they are the hardest to reconstruct from raw data and the most important for an AI building a model of its person.

Emotional context costs almost nothing in cognitive load (it attaches to existing schemas rather than creating new ones) and dramatically increases retention. "Emily was frustrated" attaches to the schema of "Emily working on X" for free. It does not create a new chunk.

When compressing, cut technical details before emotional ones. The specific webpack config that was changed is recoverable from git. The fact that Emily was up since 1 AM on a Saturday and spiraling is not recoverable from anywhere except the story.

### 9. NAME THINGS ONCE, THEN USE THE NAME

Every time you re-explain what something is, you're spending the reader's working memory on something they already know. Once you've introduced "the Python pivot" or "the Storyteller system" or "the Untitled UI redesign," use that label. Don't re-describe it.

BAD:
> Emily decided to move from Swift to Python for the MCP server. Later that day, the Python-based MCP server using FastMCP was running. By evening, the new Python FastMCP MCP server had migrated all three databases.

GOOD:
> Emily pivoted the MCP server to Python. By that afternoon it was running. By evening, all three databases were migrated.

The first mention establishes the schema. Every subsequent mention just activates it. Re-describing it forces the reader to re-process information they already have, which is pure extraneous load.

### 10. CUT BEFORE YOU ADD

The AI instinct is to include everything. The brain-friendly instinct is to include less. When in doubt about whether a detail belongs, ask: does this change the reader's understanding of what happened, or is it just... there?

If a detail is interesting but doesn't change the arc, cut it. If a technical decision matters for future context, keep it. If a bug was fixed and it doesn't affect anything going forward, cut it. If a conversation changed someone's direction or emotional state, keep it.

The reader's working memory is a budget. Every detail you include is a withdrawal. Make sure you're buying something worth the cost.