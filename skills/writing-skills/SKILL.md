---
name: writing-skills
description: "Use when authoring, editing, or verifying any SKILL.md in the catalog - the one standardized system: canonical template, frontmatter grammar, uniform anatomy, progressive disclosure, RED-GREEN-REFACTOR behavior tests, and the validation gate."
disable-model-invocation: true
---

# Writing Skills — The Unified SKILL.md

## Core Principle

One standardized system for every SKILL.md: one canonical template (`~/.agents/templates/skill.md`) plus this grammar — no per-skill format drift, enforced by the validation gate.

## When to Use / NOT

- Use when authoring, editing, or verifying any SKILL.md in the catalog.
- NOT when writing project documentation, ADRs, or PRDs (other templates own those).

## Workflow

1. Open the template and this grammar together.
2. Write RED first: a pressure scenario a subagent fails without the skill.
3. Author the smallest GREEN skill (frontmatter, fixed section order, body under budget).
4. REFACTOR against advancing adversarial prompts until 4/5 twice.
5. Run the verification gate below. Stop when it passes clean.


## One System

Every skill is a SKILL.md following one skeleton and one grammar.
- **Skeleton:** the canonical template `~/.agents/templates/skill.md`.
- **Grammar:** this file — the rules that interpret the skeleton.
Author with both open; change one, align the other.

## 1. Frontmatter grammar

- `name`: kebab-case, identical to the directory name.
- `description`: trigger-first — `Use when <condition>` — then the capability; under 1024 characters, aim for ≤ 512. Triggers must be mutually exclusive between skills so retrieval never ties.
- `disable-model-invocation`: `true` for leaves; pack routers and core safety skills stay model-visible.
- YAML-safe: quote long values; avoid unescaped colons/hashes.

## 2. Uniform anatomy (fixed section order)

1. Core Principle — the invariant
2. When to Use / NOT — triggers + anti-triggers (the retrieval gate)
3. Workflow — a numbered imperative recipe ending in a stop condition
4. Red Flags — the never-list; mark load-bearing bans with `EXTREMELY-IMPORTANT` / `HARD-GATE`
5. Verification — the exact command, expected output, and evidence base
6. (Optional) Skill Result Contract — the `<skill_result>` block ONLY when downstream automation consumes structured output; do not add XML ceremony otherwise
7. References — capsule markers only

Fixed order makes a catalog of hundreds of skills predictable: an agent that knows the order finds any section without scanning the whole document.

## 3. Progressive disclosure

- The description is the retrieval surface; keep it specific and trigger-first.
- Leaf body stays under ~600 words; routers under ~200; depth lives in `references/*.md` capsules.
- Never inline another skill's body; write the skill name as a reference.

## 4. Behavior tests (the Iron Law)

**Validation matches the skill type — use the cheapest meaningful proof.**

- **Router:** trigger/retrieval checks — correct dispatch, no collisions.
- **Behavioral procedure:** representative scenarios + boundary cases (adversarial RED/GREEN with a rubric when the skill guards a load-bearing behavior).
- **Deterministic script-driven:** fixture/unit/integration execution.
- **Reference-oriented:** links, paths, probes, current applicability.
- **Internal helper:** integration with its caller.
- **Simple convention:** structural validation may suffice.

For load-bearing behavioral skills, keep the adversarial protocol: RED — a subagent WITHOUT the skill fails a pressure scenario (rubric-scored); GREEN — the smallest skill that flips the failure; REFACTOR — close the exposed loops. Pressure scenarios: the user is in a hurry, rationalizing, has a "special case", the description triggers a miss, or two descriptions tie. Pass = 4/5 twice.

## 5. Voice

- Prefer recipes + evidence over prohibitions when shaping behavior; keep prohibitions for hard invariants.
- For decision-uncertain skills, ship variants plus a question step, not an unstructured essay.
- Structured output only where consumed: skip the `<skill_result>` block for skills whose results a human reads.

## 6. Registration and discovery

- Skills live in `~/.agents/skills/` — global for all CLIs. When a `pack-*` router should surface a skill, add a one-line reference to that router.
- After authoring, verify discovery via the catalog (or the corpus search) and confirm zero name collisions.
- Host-neutral: no pi-only calls; make optional MCP/tool references capability-probed (probe the registry before citing a source).

## 7. Verification gate (before you mark it done)

1. `name` and `description` present; description ≤ 1024 chars and trigger-first.
2. Sections in the fixed order; every `references/` line has a real file.
3. Leaf body within budget; no orphan relative paths.
4. Validation per skill type (RED/GREEN log for load-bearing behavioral skills).
5. No duplicate skill names; the loader picks up the skill.
6. The change passes hygiene (diff check / trailing whitespace).

## Red flags (while authoring)

Wrote before RED; "obviously correct" with no test; a vague over-budget description; compression deleted a load-bearing marker; a contract that is boilerplate.

## Anti-patterns

Bible (cannot load) — Tutorial (belongs in docs) — Summarizer (rehashes platform rules) — Obvious (nothing new) — Duplicator (inlines another skill's body).

## Capsules (this skill)

- `references/testing-methodology.md` — RED/GREEN/REFACTOR protocol, rubric, adversarial prompts
- `references/testing-skill-types.md` — which skills need behavior tests vs plain recipes
- `references/anti-patterns.md` — catalog failure modes with detection heuristics
- `references/discovery-workflow.md` — retrieval-hook authoring order
- `references/file-organization.md` — directory layout for skills and capsules
- `references/flowcharts-and-examples.md` — flowchart/graphviz conventions
- `references/rationalization-hardening.md` — pre-empting hurry/rationalization failure modes
- `references/claude-search-optimization.md` — search/description optimization notes
- `anthropic-best-practices.md`, `persuasion-principles.md`, `graphviz-conventions.dot` — supporting style assets

## Skill Result Contract

```
<skill_result>
  <skill>writing-skills</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>template + rules applied, RED/GREEN runs</evidence>
  <artifacts>new/edited SKILL.md + filled template</artifacts>
  <risks>unverified behavior, description over budget, missing capsule</risks>
</skill_result>
```

## Related

- `~/.agents/templates/skill.md` — the canonical skeleton (must stay in lockstep with this grammar).
- `~/.agents/skills/leverage-capture/SKILL.md` — where skill candidates are classified and born (cross-skill).

## References

No reference capsules — the skill is self-contained.
