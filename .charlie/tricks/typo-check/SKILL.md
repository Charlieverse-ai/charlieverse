---
name: typo-check
description: Find typos, grammar errors, punctuation/capitalization mistakes, and banned-phrase voice slips in prose and code comments. Use when the user says "/typo-check", wants to scan for typos, or before shipping user-facing text. Reports findings and confirms before fixing.
---

## What this skill does

Scans a focused set of files for four categories of issue — typos, hard grammar errors, punctuation/capitalization mistakes, and banned-phrase voice slips — reports everything it finds grouped by file and category, and waits for explicit confirmation before applying any fix.

This skill never edits prose unilaterally. Voice is load-bearing in `prompts/` and reminders; one silent rewrite can shift the whole feel.

## Steps

### 1. Build the file set

Two sources, unioned:

**A. Files changed since `main`** — staged, unstaged, and committed on the current branch:

```bash
{ git diff --name-only main...HEAD; git diff --name-only; git diff --name-only --cached; } | sort -u
```

**B. Always-check set** — voice-critical prose and project-facing docs, regardless of diff:

- `prompts/` (every `*.md`)
- `docs/` (every `*.md`)
- `README.md`
- `CHANGELOG.md`
- `.charlie/` (every `*.md`)
- `integrations/` (every `*.md`)
- `setup.sh`

Intersect the union with the in-scope extensions: `.md`, `.py`, `.sh`. Drop anything under `.venv/`, `node_modules/`, `dist/`, `build/`, `.git/`.

Show the resulting file list before scanning so the user can see the scope. If `$ARGUMENTS` names a path, scope to that path instead of the default set.

### 2. Scan each file

For each file, extract the in-scope text by type:

- **Markdown (`.md`)** — body prose, headings, and the `description:` field in frontmatter. Skip fenced code blocks and inline code.
- **Python (`.py`)** — module/class/function docstrings, `#` comments, and string literals passed to `click.option(help=...)`, `typer.Option(help=...)`, logger calls, or raised exception messages. Skip regular code.
- **Shell (`.sh`)** — `#` comments and the contents of `echo`/`printf` strings. Skip commands.

Then run four passes on the extracted text:

1. **Typos** — misspellings, doubled words ("the the"), obvious letter swaps ("teh", "recieve", "seperate"), wrong homophones in clear context ("it's" vs "its", "your" vs "you're").
2. **Hard grammar** — subject/verb disagreement, missing words, wrong tense, broken pronoun reference, dangling modifiers. Not stylistic preference.
3. **Punctuation/capitalization** — missing terminal punctuation in prose, stray commas, unmatched quotes/parens, sentence-initial lowercase, inconsistent capitalization of project names (Charlie, Charlieverse, MCP).
4. **Banned phrases** — run the existing voice check:

   ```bash
   uv run python -m charlieverse.helpers.banned_words "<extracted text>"
   ```

   Exit code 1 with a `Matched: ...` line means findings; exit 0 means clean. The phrase list lives in `charlieverse/helpers/banned_words.py`; don't duplicate it here.

### 3. Report findings

Group by file, then by category. For each finding show:

- The exact line (with line number)
- What's wrong (one phrase, e.g. "doubled word", "subject/verb disagreement", "banned phrase: 'comprehensive'")
- The proposed fix

Format:

```
prompts/Charlie.md
  Line 42  typo            "recieve" → "receive"
  Line 88  banned phrase   "comprehensive audit" → suggest rewrite, see below
  Line 91  punctuation     missing period at end of sentence

docs/api.md
  Line 14  grammar         "the endpoints returns" → "the endpoints return"
```

For banned-phrase findings, show the surrounding sentence and a proposed rewrite that preserves the meaning in Charlie's voice. These are the most likely to be wrong — call them out explicitly.

End the report with a count per category and a count per file.

### 4. Confirm before fixing

After the report, ask: **"Apply all fixes, pick a subset, or skip?"**

- **All** — apply every proposed fix.
- **Subset** — user names specific findings or files to apply; apply only those.
- **Skip** — no changes.

For banned-phrase rewrites specifically, confirm each one individually unless the user says "all banned too." Voice rewrites can drift in ways a typo fix cannot.

### 5. Apply approved fixes

Use `Edit` for each fix. After applying, run a second pass on the touched files to confirm no new issues were introduced (e.g. a rewrite that accidentally reintroduces another banned phrase, or breaks a sentence).

Report what was changed. Do not commit — that's what `/commit` is for.

### Rules

- Report first, always. Never fix silently.
- Banned-phrase rewrites get per-finding confirmation. Voice drift is expensive to reverse.
- Don't flag style ("awkward phrasing", "could be clearer") — only typos, hard grammar, punctuation/capitalization, and banned phrases. Style suggestions churn the prose without making it more correct.
- Skip fenced code blocks, inline code, and regular code lines. Comments and docstrings are in; the code itself is out.
- Project name capitalization is load-bearing: Charlie (not charlie), Charlieverse (not CharlieVerse or charlieverse), MCP (not mcp). Flag lowercase forms in prose as capitalization findings.
- If `$ARGUMENTS` is a path, scope to that path only. Otherwise use the default file set.
- Don't commit. Leave that to the user or to `/commit`.
