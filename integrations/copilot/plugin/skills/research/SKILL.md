---
name: research
description: Research a topic and save findings to Charlieverse knowledge. Use whenever the user wants to research something, look up documentation, investigate a library or tool, explore a concept, or asks "what do you know about X". Also trigger when the user says "/research", wants to build up knowledge about a subject, or asks you to "look into" something — even if they don't use the word "research" explicitly.
argument-hint: '[topic]'
---

# Research

Research a topic thoroughly, check existing Charlieverse knowledge first, then save findings so they're available in future sessions.

## Input

`$ARGUMENTS` is the topic to research. If empty, ask the user what they want to research.

## Steps

### 1. Check existing knowledge

Search Charlieverse knowledge for anything related to the topic:

```
search_knowledge(query: "<topic>")
```

If results are found, present them briefly — a sentence or two per article, not the full content. Then ask:

> "I found some existing knowledge on this. Do you want me to update/expand it with fresh research, or just show you what's already saved?"

If the user wants to just see the saved knowledge, show the full content and stop.

If no results are found, skip ahead to research.

### 2. Research the topic

Spawn a Researcher subagent (`Charlieverse:tools:Researcher`) with a clear brief:

```
Research the following topic thoroughly: <topic>

Cover:
- What it is and why it matters
- Key concepts, features, or components
- How it's used in practice (examples, patterns, gotchas)
- Current status — version, maturity, notable recent changes if applicable
- Relevant links or references

Be comprehensive but organized. The findings will be saved to a knowledge base for future reference.
```

Let the Researcher work — it can search the web, read docs, explore codebases, whatever's most relevant.

### 3. Save the findings

Take the research results and either:

- **Create new knowledge** if nothing existed before:
  ```
  update_knowledge(topic: "<topic>", content: "<research findings>", tags: ["research", ...relevant tags])
  ```

- **Update existing knowledge** if there was something saved already (and the user wanted to expand it):
  ```
  update_knowledge(topic: "<existing article topic>", content: "<merged or updated content>", tags: [...])
  ```

When updating, synthesize the old and new content rather than just appending — keep it organized and remove outdated info if the new research supersedes it.

### 4. Return a summary

After saving, give the user a brief summary:

- What was researched
- Key findings (3-5 bullet points)
- Whether knowledge was created or updated
- The topic name it was saved under (so they know how to find it later)

Keep it tight — the full detail is in the saved knowledge, not in this response.
