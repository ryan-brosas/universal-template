# skill.md - canonical SKILL.md template

Copy as `<skill-dir>/SKILL.md`. Follow `skills/writing-skills/SKILL.md`;
omit sections that do not earn their load. This is a menu, not a required sequence.

---
name: <kebab-case-name>
description: "Use when <trigger>; state the capability unlocked." # strict YAML string
invocation: manual # entry | internal | manual | vendor; choose from actual callers
disable-model-invocation: true # required for internal/manual; entry stays visible
# Cold source evidence only: kind: foundation requires a *-foundation name,
# invocation: manual, disable-model-invocation: true, and references/index.md.
---

# <Readable Title>

## Purpose
The missing task context or expensive failure this skill addresses. Omit generic
engineering advice already supplied by the model or project.

## When to Use / NOT
- **Use when:** <distinguishable trigger>
- **NOT when:** <boundary or another owner's precedence>

## Approach
Supply useful decisions, shortcuts, and non-obvious mechanics. Use ordered steps
only where ordering matters; leave valid implementation choices with the model.

## Boundaries
Safety, protocol integrity, or demonstrated expensive failures only. Omit if none.

## Verification
Name evidence of the task outcome, not compliance with these instructions.
Use deterministic checks for exact contracts; model review for meaning and tradeoffs.

## References
- `references/<capsule>.md`, what it adds and when to load it.

## Notes for the author (delete after filling)
- State the lift hypothesis during authoring: what work disappears, what unique
  context is supplied, and which decisions remain with the model. Keep evaluation
  evidence outside the runtime loader unless it directly helps the task.
- Match evidence to skill type. Compare representative work with/without a candidate
  for hot promotion, material load-bearing changes, overlap, or costly loaders.
  A simple reference does not need an A/B ritual. No new required evaluation CI.
- Aim for leaf bodies under about 600 words and routers under about 200; measure
  usefulness, not size alone. Load references selectively, not as prerequisites.
- `name` equals the directory name; strict YAML scalar/boolean types are required.
- Only visible local `entry` metadata is generically hot. Internal, manual,
  vendor, and foundation leaves stay cold in the generic surface. Promote only
  when recurring need and distinct lift justify exposure.
- For foundations, follow `skills/writing-skills/references/foundation-kind.md`.
- Verify local references, metadata, discovery, callers, and diff hygiene.
