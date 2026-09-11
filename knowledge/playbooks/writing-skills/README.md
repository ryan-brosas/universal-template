---
title: writing-skills
summary: Use when creating, editing, auditing, or verifying a skill or SKILL.md—including trigger descriptions and routing overlap—or promoting a demonstrated procedure; preserve the catalog contract and require evidence of task lift for material hot changes.
kind: playbook
---

# Writing Skills

A skill earns its load by improving work, not by making the model obey more rules.
Use this for pack/playbook authoring, not ordinary project documentation. Start with
`../../../templates/skill.md`; omit sections that add no task-specific value.

## Author for lift

Identify what the model repeatedly gets wrong or rediscovers, what unique context
is missing, and what work the candidate should remove. Preserve decisions that
belong to the model or project. Reusable code and exact recurring checks belong
in implementation or gates rather than prose.

For hot promotion, material changes to load-bearing skills, overlapping owners,
large loaders, or observed slowdown, compare a representative task without the
skill and with the smallest candidate. Judge outcome quality, errors, turns,
tool calls, loaded context, and unintended artifacts or effects. Use the same
starting conditions; do not force a baseline failure or reward citation of rules.
Keep, compress, demote, merge, or retire based on the tradeoff. An unmeasured
candidate is not demonstrated lift.

Select the cheapest meaningful evidence by skill type. References need relevant,
usable information and valid links; routers need reliable selection; deterministic
helpers need execution tests. Guardrails need evidence that an expensive failure
is prevented, including legitimate exceptions. Pressure tests serve that purpose,
not universal obedience testing. See `references/lift-evaluation.md` when designing
a comparison. Evaluation is selective authoring work, not mandatory CI or a runtime
scoring engine.

## Metadata and discovery

- Visible routers live at `../../../skills/<name>-pack/SKILL.md`. Use a
  directory-matching `name`, trigger-first `description` under 1024 characters
  (aim for 512 or fewer), and `invocation: entry`. State precedence for overlap.
- Specialists live at `../<name>/README.md` with `title`, `summary`, and
  `kind: playbook`. Omit skill-discovery fields and `SKILL.md`; merely hiding a
  description does not prevent discovery. Preserve attribution and license data.
- Link each specialist from one existing pack's cold index. Cross-pack links may
  share the same procedure, never copies. New visible packs require demonstrated
  routing need; useful specialists do not automatically earn startup exposure.
- Keep helpers/assets with their procedure. Resolve all paths from that directory,
  not the router. Read source evidence directly when a procedure needs it rather
  than adding a permanent source summary.
- Parse strict YAML with appropriate scalar types. Package-owned and private
  skills are separate: preserve them and use supported host filters rather than
  changing installed packages or copying their instructions.

## Keep invocation small

Aim for leaf bodies under about 600 words and routers under about 200. These are
review targets, not proof of value. Keep the loader usable alone; put deep mechanics
in focused references loaded only for the active question. Do not duplicate live
tool schemas, another skill, or the global constitution. Use host-neutral guidance
and probe optional capabilities. Add structured output only for a real parser.

Prefer choices and evidence over prohibitions. Reserve hard constraints for safety,
protocol integrity, or demonstrated expensive failures, not architectural taste.

## Verify and stop

Choose checks for the destination, not the shell's current directory. Inspect
metadata, names, links, discovery, and callers in the changed checkout directly.
Use that project's existing checks where relevant; this template has no catalog
generator or custom skill-validation pipeline. Do not modify the global skill
tree to validate an unrelated external skill.

Confirm referenced files exist, intended host discovery works, and changed callers
still work. Only pack routers belong in the template skill-discovery tree;
playbooks stay outside it. Check diff hygiene. Review
prose using `../house-writing-style/README.md`; models review
meaning, scripts check exact contracts. Report evidence, unmeasured claims, and
remaining limitations separately.
