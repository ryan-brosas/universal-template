<!-- capsule-v2 -->
# Skill-content invariant gate — how do you gate an agent skill's prose for safety properties without running the agent?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** An agent skill is prose — its safety properties (verify auth before writes, prefer surgical edits, never create a parallel system) have no function to unit-test. How do you pin those properties structurally so a careless edit cannot silently remove a safety rule?

## Content invariants as regex needles, negative pins, and registration parity
**Path/Symbol:** `scripts/validate-notion-workspace-skill.mjs` (whole, 78L) — skip gate :15-18, PASS/FAIL reporter :20-27, safety needles :39-52, hub-structure needles :53-63, negative pins :69-73, registration parity :74-75.
**Signature:** `node scripts/validate-notion-workspace-skill.mjs` (no args; root fixed to the repo via `new URL('..', import.meta.url).pathname`).
**Data Shape:** input is one SKILL.md text plus its router SKILL.md and `packs.json` catalog entry; each check is `(boolean condition, string message)` printed as `PASS <message>` / `FAIL <message>`; a `failures` counter drives exit 0/1.

### Decisive source
```js
// :44-52 safety properties pinned as regex needles over the skill prose
check(
  /GitHub/.test(skill) && /ryan-workspace/.test(skill) && /source of truth/i.test(skill),
  'skill preserves source-of-truth boundaries'
)
check(/page edit/.test(skill) && /page update/.test(skill), 'skill prefers surgical edits over full-page replacement')
check(
  /duplicate/i.test(skill) && /destructive/i.test(skill) && /credential/i.test(skill),
  'skill prevents duplicate systems and protects destructive actions and credentials'
)
// :69-73 NEGATIVE pins — the prose must NOT say this
check(!/Personal Brand/.test(skill), 'skill does not name Personal Brand as a content system')
check(
  /never create a parallel|do not create.{0,40}(parallel|another hub)/i.test(skill),
  'skill prohibits creating a parallel central hub'
)
// :74-75 registration parity
check(router.includes('notion-workspace:'), 'authoring router lists notion-workspace')
check(authoring?.members.includes('notion-workspace'), 'catalog assigns notion-workspace once')
```

## Flow
1. Skip gate on the skill file itself (:15-18) — the deepest path — so checkouts without `.pi/skills` `[skip]` exit 0 (same command in dev tree / published checkout / CI).
2. Positive content pins: public `name:` frontmatter; auth verification (`notion-cli auth status`) AND search-before-fetch; source-of-truth boundaries; surgical-edit preference; duplicate/destructive/credential protection; flexible hub sections (Projects/Tasks/Notes/Content/Learning); single central hub; reuse of the existing content system.
3. Negative content pins: must NOT name the retired system; must contain an explicit prohibition of parallel hubs (regex accepts either of two phrasings).
4. Registration parity: the pack router must list the skill; the catalog must assign it exactly once — the same membership algebra validate-skill-packs enforces globally, pinned per-skill.
5. Exit: `failures ? 1 : 0` with a final `notion workspace skill: all pass|FAIL` line.

## Invariant
- Safety properties that live only in prose are still enforceable: pin the PROPERTY's vocabulary (auth check, search-before-fetch, surgical edit, prohibition phrasing) as needles, so deleting the safety sentence fails the gate.
- Negative pins matter as much as positive ones: retired names and forbidden behaviors are pinned by ABSENCE.
- A skill is not just its file: router listing + catalog membership are part of the contract (registration parity).
- This gate uses its own PASS/FAIL reporter vocabulary, NOT the shared `createReporter` `[ok]/[fail]` kernel from validate-common.mjs — a deliberate one-off (single-file scope), but a vocabulary inconsistency across the fleet.

## Probe
No direct unit test exists for this script at this pin (recorded caveat). Executed live probe:
```
node scripts/validate-notion-workspace-skill.mjs
# → [skip] .pi/skills is not in this checkout; notion-workspace checks run in the development tree
# → exit 0
```

## Retrieve
`search_graph(project="pi-acp", q="validate-notion-workspace-skill notion-workspace source of truth parallel hub", mode="ids")` — revalidate at the current pin (graph unavailable passes 5–8; direct read is the authority).

## Adopt/Adapt/Omit Verdict
**Adapt.** Adopt: pinning agent-skill safety prose as regex needles (positive property vocabulary + negative retired-vocabulary pins + registration parity) in a pure-read gate that skips on its deepest path. Adapt: prefer the shared `[ok]/[fail]` reporter kernel for fleet consistency; the repo-specific Notion workspace nouns are examples, not the pattern. Omit: nothing structural — the whole gate is the pattern.
