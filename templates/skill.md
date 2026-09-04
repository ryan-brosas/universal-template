# skill.md - canonical SKILL.md template

Copy as `<skill-dir>/SKILL.md` and fill only what earns its place. The
`writing-skills` grammar governs details; omit empty sections.

---
name: <kebab-case-name>
description: "Use when <trigger>; state the capability unlocked."
invocation: entry # entry | internal | manual | vendor
# Host visibility. Required for internal/manual skills:
# disable-model-invocation: true
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
Load-bearing bans only. Mark a hard gate only when the boundary is objective.

## Verification
Name the evidence that proves the outcome. Use deterministic commands only for
exact contracts; use model review for semantics and prose.

## References
- `references/<capsule>.md`, what the capsule adds.

Keep leaf bodies under about 600 words; depth lives in capsules.

## Notes for the author (delete after filling)
- `name` must equal the folder name.
- The model chooses `invocation` from real callers and visibility needs.
- Every cited `references/` file must exist.
