---
name: writing-skills
description: "Use when authoring, editing, or verifying a SKILL.md, or promoting a demonstrated procedure into a skill; select evidence of task lift and preserve the catalog contract."
invocation: manual
disable-model-invocation: true
---

# Writing Skills

A skill earns its load by improving work, not by making the model obey more rules.
Use this for skill authoring, not ordinary project documentation. Start with
`../../templates/skill.md`; omit sections that add no task-specific value.

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

- `name`: kebab-case, identical to the directory name.
- `description`: trigger-first (`Use when ...`), under 1024 characters; aim for
  512 or fewer. Triggers must be distinguishable enough for reliable selection.
  For legitimate overlap, state precedence or use one small router.
- `invocation`: `entry`, `internal`, `manual`, or `vendor`, chosen from actual
  callers. Only visible local entries are generically hot. Internal/manual
  skills require `disable-model-invocation: true`; vendor visibility follows
  its integration. Hot promotion needs recurring use and distinct demonstrated
  lift, not automatic publication of every useful skill.
- `kind: foundation`: only for cold source evidence; follow
  `references/foundation-kind.md` when authoring one.
- Parse strict YAML: known scalar fields are strings; visibility flags are real
  booleans. Quote values containing colon-space or hash syntax.

## Keep invocation small

Aim for leaf bodies under about 600 words and routers under about 200. These are
review targets, not proof of value. Keep the loader usable alone; put deep mechanics
in focused references loaded only for the active question. Do not duplicate live
tool schemas, another skill, or the global constitution. Use host-neutral guidance
and probe optional capabilities. Add structured output only for a real parser.

Prefer choices and evidence over prohibitions. Reserve hard constraints for safety,
protocol integrity, or demonstrated expensive failures, not architectural taste.

## Verify and stop

Run `python3 scripts/skill-validator.py`, regenerate catalogs with
`python3 scripts/skill-catalog.py generate`, then check with `generate --check`.
Confirm referenced files exist, discovery selects exactly one hot/cold set, and
changed callers still work. Check diff hygiene. Review prose using
`../house-writing-style/SKILL.md`; models review meaning, scripts check exact
contracts. Report evidence, unmeasured claims, and remaining limitations separately.
