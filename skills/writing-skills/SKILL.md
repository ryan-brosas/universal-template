---
name: writing-skills
description: "Use when authoring, editing, or verifying any SKILL.md in this catalog: canonical template, frontmatter grammar, uniform anatomy, progressive disclosure, and the validation gate. Also when creating a new skill from a demonstrated procedure."
invocation: entry
---

# Writing Skills, The Unified SKILL.md

## Core Principle

One standardized system for every SKILL.md: one canonical template (`../../templates/skill.md`) plus this grammar, no per-skill format drift, enforced by the validation gate.

## When to Use / NOT

- Use when authoring, editing, or verifying any SKILL.md in the catalog.
- NOT when writing project documentation, ADRs, or PRDs (other templates own those).

## Workflow

1. Open the template and this grammar together.
2. Write RED first: a pressure scenario a subagent fails without the skill.
3. Author the smallest GREEN skill (frontmatter, only the sections it earns, body under budget).
4. REFACTOR against advancing adversarial prompts until 4/5 twice.
5. Run the verification gate below. Stop when it passes clean.


## One System

Every skill is a SKILL.md governed by one grammar and supported by one adaptable template.
- **Template:** `../../templates/skill.md` shows the available sections.
- **Grammar:** this file decides which sections and fields the skill earns.
Author with both open; change one, align the other.

## 1. Frontmatter grammar

- `name`: kebab-case, identical to the directory name.
- `description`: trigger-first, `Use when <condition>`, then the capability; under 1024 characters, aim for ≤ 512. Triggers must be mutually exclusive between skills so retrieval never ties.
- `invocation`: local ownership, one of `entry`, `internal`, `manual`, or `vendor`. The model chooses the class from the real caller and trigger.
- `kind: foundation`: required only for cold `*-foundation` leaves. Foundations live in the unified `skills/` tree but are manual and hidden; see `references/foundation-kind.md`.
- `disable-model-invocation`: the host visibility field. `entry` stays visible; `internal`, `manual`, and every foundation stay hidden; vendor visibility follows the integration.
- YAML is parsed strictly with PyYAML. Known scalar fields must be strings and
  `disable-model-invocation`/`x-manual-only` must be real booleans, not quoted
  lookalikes. Quote values containing colon-space or hash syntax.

## 2. Minimum useful content (conditional anatomy)

Every skill needs good frontmatter and the minimum body that earns its load.
Add sections only when they carry non-obvious value:

| Skill kind | Usually needs |
|---|---|
| Tool / capability | When to use, how to invoke, stop condition |
| Reference / map | What it contains, where to look |
| Complex procedure | When/not, workflow, verification, references |
| Cognitive nudge | Probably should not be a skill |

Common sections when earned: Core Principle, When to Use / NOT, Workflow, Red
Flags, Verification, References. Skip empty or generic sections. Do not force
uniform boilerplate.

Structured `<skill_result>` output only when a real downstream consumer parses
it. Human-read skills return normal prose.

## 3. Progressive disclosure

- The description is the retrieval surface; keep it specific and trigger-first.
- Leaf body stays under ~600 words; routers under ~200; depth lives in `references/*.md` capsules.
- Never inline another skill's body; write the skill name as a reference.

## 4. Behavior tests (the Iron Law)

**Validation matches the skill type, use the cheapest meaningful proof.**

- **Router:** trigger/retrieval checks, correct dispatch, no collisions.
- **Behavioral procedure:** representative scenarios + boundary cases (adversarial RED/GREEN with a rubric when the skill guards a load-bearing behavior).
- **Deterministic script-driven:** fixture/unit/integration execution.
- **Reference-oriented:** links, paths, probes, current applicability.
- **Internal helper:** integration with its caller.
- **Simple convention:** structural validation may suffice.

For load-bearing behavioral skills, keep the adversarial protocol: RED, a subagent WITHOUT the skill fails a pressure scenario (rubric-scored); GREEN, the smallest skill that flips the failure; REFACTOR, close the exposed loops. Pressure scenarios: the user is in a hurry, rationalizing, has a "special case", the description triggers a miss, or two descriptions tie. Pass = 4/5 twice.

## 5. Voice

- Prefer recipes + evidence over prohibitions when shaping behavior; keep prohibitions for hard invariants.
- For decision-uncertain skills, ship variants plus a question step, not an unstructured essay.
- Structured output only where consumed: skip the `<skill_result>` block for skills whose results a human reads.

## 6. Registration and discovery

- Skills and cold foundations share the canonical `../` tree. Eager or
  unverified hosts receive only the tracked hot set: operational and not hidden.
  Hidden operational skills and foundations stay cold; use the filtered symlink
  route in `../../README.md`.
- Foundations are found by explicit catalog/filesystem search and loaded one capsule at a time.
- When a `pack-*` router should surface an operational skill, add a one-line reference to that router.
- After authoring, verify discovery via the catalog (or the corpus search) and confirm zero name collisions.
- Host-neutral: no pi-only calls; make optional MCP/tool references capability-probed (probe the registry before citing a source).

## 7. Verification gate (before you mark it done)

1. Frontmatter parses as strict YAML; known fields have the required scalar or
   boolean type; `name` and `description` are present and trigger-first.
2. Every section carries useful content for that skill kind; every `references/` line has a real file.
3. Leaf body within budget; no orphan relative paths.
4. Validation per skill type (RED/GREEN log for load-bearing behavioral skills).
5. No duplicate skill names; the loader picks up the skill in exactly one of
   the disjoint hot/cold sets.
6. The change passes hygiene (diff check / trailing whitespace).
7. The model reviews prose in context with `skills/house-writing-style/SKILL.md`; style preferences do not become mechanical publication failures.

## Red flags (while authoring)

Wrote before RED; "obviously correct" with no test; a vague over-budget description; compression deleted a load-bearing marker; a contract that is boilerplate.

## Anti-patterns

Bible (cannot load), Tutorial (belongs in docs), Summarizer (rehashes platform rules), Obvious (nothing new), Duplicator (inlines another skill's body).

## Capsules (this skill)

- `references/testing-methodology.md`, RED/GREEN/REFACTOR protocol, rubric, adversarial prompts
- `references/testing-skill-types.md`, which skills need behavior tests vs plain recipes
- `references/anti-patterns.md`, catalog failure modes with detection heuristics
- `references/discovery-workflow.md`, retrieval-hook authoring order
- `references/file-organization.md`, directory layout for skills and capsules
- `references/flowcharts-and-examples.md`, flowchart/graphviz conventions
- `references/rationalization-hardening.md`, pre-empting hurry/rationalization failure modes
- `references/claude-search-optimization.md`, search/description optimization notes
- `references/foundation-kind.md`, cold source foundations versus explicitly promoted procedures
- `anthropic-best-practices.md`, `persuasion-principles.md`, `graphviz-conventions.dot`, supporting style assets


## Related

- `../../templates/skill.md`, the canonical skeleton (must stay in lockstep with this grammar).
- `../leverage-capture/SKILL.md`, where skill candidates are classified and born (cross-skill).

## References

The capsule list above is the progressive-disclosure index for this skill.
