# skill.md — canonical SKILL.md template

Copy as `<skill-dir>/SKILL.md` and fill every block. The `writing-skills` grammar governs the details; this file is the mandated skeleton for every skill in this catalog.

---
name: <kebab-case-name>
description: "Use when <trigger> — the <capability unlocked>. Trigger-first; total under 1024 characters."
# Leaves only: disable-model-invocation: true (routers + core safety skills omit it)
---

# <Readable Title>

## Core Principle
One or two sentences: the invariant the loaded skill holds.

## When to Use / NOT
- **Use when:** <precise trigger conditions — the retrieval hook>
- **NOT when:** <boundary cases — prevents wasteful loads>

## Workflow
Numbered imperative steps, ending in a stop condition or the final output.
1. …
2. …

## Red Flags
- **Never do:** <constraints>; mark load-bearing rules with `EXTREMELY-IMPORTANT` / `HARD-GATE`.

## Verification
The exact check(s) before claiming it works: command, expected output, how to cite the evidence.

## Skill Result Contract

```
<skill_result>
  <skill><name></skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References
- `references/<capsule>.md` — what the capsule adds (probes, invariants, sources).

One capsule per deep seam; keep the leaf under ~600 words.

## Notes for the author (delete after filling)
- name must equal the folder name, kebab-case.
- description: "Use when …" is the mandatory first phrase; it is what the retriever matches.
- Required order = Core Principle → When to Use / NOT → Workflow → Red Flags → Verification → Skill Result Contract → References. Do not reorder.
- Every `references/` line must point to a real file in `references/`.