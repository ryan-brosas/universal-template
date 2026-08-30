---
name: brainstorming
description: "Use when a rough idea needs clarification before implementation — optional collaborative questioning and variant exploration when the goal or approach is ambiguous."
---

# Brainstorming

Optional — skip when the user gave a clear, concrete request.

## When to Use

Rough idea, vague feature request, or multiple plausible approaches where the choice is load-bearing. "What if we…", "I'm thinking…" with real ambiguity.

## When NOT to Use

Bug fixes with known root cause; mechanical refactor with obvious verification; trivial one-liner; well-defined requests — go straight to `codebase-driven-development`.

## Core Principle

**Classify unknowns when they exist.** Don't block implementation when they don't.
- **Known knowns** — in the prompt; implement.
- **Known unknowns** — ask the user (one question at a time when non-obvious).
- **Unknown knowns** — show 2–4 cheap variants or point at a reference.
- **Unknown unknowns** — ask the model to teach you the criteria.

A simpler approach often exists — say so.

## Workflow

1. **Map unknowns** — only when ambiguous; state assumptions.
2. **Variants** — for novel or design-heavy work, show 2–4 cheap variants before recommending one.
3. **Interview** — one question at a time on architecture, data model, or UX when needed.
4. **Validate** — check-in: "does this match what you wanted?" when ambiguity remains.
5. **Implement** — via `codebase-driven-development` (foundations + nearest code as context).

## Cheat Sheet

| Situation                                 | Default action                                   |
|-------------------------------------------|--------------------------------------------------|
| Clear, concrete request                   | Skip brainstorm; implement.                      |
| Spec concrete, single-file                | Skip brainstorm, implement.                      |
| Spec concrete, multi-file or design-heavy | One question on the riskiest unknown, then build. |
| Spec vague                                | Variants first, then interview.                  |
| "Sanity check" / "prototype"              | Use `prototype` skill.                           |
| Multiple valid approaches                 | Show 2–4 variants with trade-offs.               |
| New library / framework                   | Point at official docs/source.                   |

## Red Flags

Skipping variants when a design decision is genuinely load-bearing; asking 5 questions in one message when one would do; "we can add caching later" hand-waving in production-bound design.

## Anti-Patterns

**The 200-word answer** when 2–4 variants surface the same trade-off; **the leading question** collapses the brainstorm; **the silent assumption** picks a stack without naming it; **blocking clear work** behind a design ritual the user didn't ask for.

## Skill Result Contract

```xml
<skill_result>
  <skill>brainstorming</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Unknowns mapped when ambiguous, variants shown if novel</evidence>
  <artifacts>Design summary or "skipped — request was concrete"</artifacts>
  <risks>Unresolved questions, scope creep, or none</risks>
</skill_result>
```

## Verification

Unknowns classified when ambiguity existed; 2–4 variants shown for novel or design-heavy work when needed; handoff to `codebase-driven-development` without unnecessary delay.

## References

N/A — no reference files; this skill is self-contained.
