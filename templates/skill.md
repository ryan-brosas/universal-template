# skill.md — canonical SKILL.md template

Copy as `<skill-dir>/SKILL.md` and fill only what earns its place. The
`writing-skills` grammar governs details; omit empty sections.

---
name: <kebab-case-name>
description: "Use when <trigger> — the <capability unlocked>. Trigger-first; total under 1024 characters."
# Hide cold/manual skills: disable-model-invocation: true
---

# <Readable Title>

## Core Principle
One or two sentences when the skill guards a non-obvious invariant.

## When to Use / NOT
- **Use when:** <precise trigger>
- **NOT when:** <boundary>

## Workflow
Numbered steps ending in a stop condition. Omit for pure reference maps.

## Red Flags
Load-bearing bans only. Mark with `EXTREMELY-IMPORTANT` / `HARD-GATE` when needed.

## Verification
Exact command(s) and expected evidence. Omit when obvious from workflow.

## References
- `references/<capsule>.md` — what the capsule adds.

Keep leaf bodies under ~600 words; depth lives in capsules.

## Notes for the author (delete after filling)
- `name` must equal the folder name (kebab-case).
- Description must start with `Use when …`.
- Add `<skill_result>` XML only when a machine parses the output.
- Every `references/` line must point to a real file.
