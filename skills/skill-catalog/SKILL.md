---
name: skill-catalog
description: "Use when no visible skill clearly owns a task, a named technology may have a hidden specialist, the user asks what capabilities exist, or selection seems wrong. Search cold SKILL.md frontmatter; load only the narrowest match."
invocation: entry
---

# Find the missing specialist

Use this as a fallback bridge, not a phase before every task. A visible skill that
clearly owns the request wins. The canonical inventory is the parent directory
(`../`); generated catalogs are optional human views.

## Route

1. **Handle this checkout explicitly.** Work on `~/.agents`,
   `universal-template`, `AGENTS.md`, prompts, skills, templates, MCP declarations,
   or publication tooling loads `../template-maintenance/SKILL.md`. Creating,
   editing, auditing, or verifying a skill also loads
   `../writing-skills/SKILL.md`.
2. **Search metadata first.** Search bounded skill names and frontmatter
   descriptions using distinctive task nouns, product names, file formats, and
   user intent. Inspect only the best 1–3 candidates before choosing.
3. **Prefer the narrow owner.** Choose an operational specialist over a generic
   guide. Named languages and frameworks route to an existing matching
   `*-coding-practices` leaf; when none exists, search for a matching operational
   specialist or foundation and use a foundation only when source-specific
   evidence helps. Exact tools, document/media formats, and service names route
   to the matching specialist. Session-to-skill or retrospective requests route
   to `../session-improvement-compiler/SKILL.md`.
4. **Load only what helps.** Read the selected `SKILL.md`, then only references
   it identifies for the active question. Combine skills only when they own
   distinct parts of the request.

Foundations are cold, source-specific evidence. Use one only when porting a
pattern or filling a real source gap: inspect its topic map, search reference
filenames/headings, and open 1–3 matching capsules. Revalidate source pins before
relying on historical claims. If no specialist adds useful context, continue
from project source rather than forcing a match.

## Maintenance and verification

Frontmatter owns names, descriptions, invocation, and visibility. Hot promotion
requires recurring need, reliable selection, and distinct demonstrated lift;
missing telemetry is unknown, not evidence of disuse. After metadata changes,
check explicit callers and host visibility, then run this checkout's publication
checks. `../../scripts/skill-catalog.py` remains an optional diagnostic for list,
search, context, and invocation-size reports; it is not a runtime prerequisite.
