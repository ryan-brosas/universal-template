---
name: source-driven-development
description: "Use when shipping code that depends on unfamiliar libraries, external APIs, or framework behavior: cite the source or mark the decision unverified; route discovery to the research pack."
disable-model-invocation: true
---

# Source-Driven Development (gate)

This is a delivery-time gate, not a research workflow. Discovery belongs to the research leaves (`evidence-router`, `codex-websearch`, `opensrc`, `grill-with-docs`); this skill only enforces the rule that non-trivial external decisions are not shipped on a guess.

## Iron Rule

For any non-trivial external API, framework, or version decision:

- Cite the authoritative source (URL, docs, or local precedent), **or**
- Mark the decision `[UNVERIFIED: reason]` explicitly.

No citation and no unverified label → the claim does not ship.

## Core Principle

This is a delivery-time gate, not a research workflow: non-trivial external decisions
are not shipped on a guess. Cite the authoritative source (URL, docs, or local
precedent), or mark the decision `[UNVERIFIED: reason]` explicitly — no citation and no
unverified label means the claim does not ship.

## When to Use / NOT

- **Use when:** shipping code that depends on unfamiliar libraries, external APIs, or
  framework behavior — any non-trivial external API, framework, or version decision.
- **NOT when:** doing the discovery itself — discovery belongs to the research leaves
  (`evidence-router`, `codex-websearch`, `opensrc`, `grill-with-docs`); this skill only
  enforces the rule at delivery time.

## Workflow

1. Identify every non-trivial external API, framework, or version decision in the
   change.
2. Route discovery to the matching research leaf (table below) instead of re-deriving a
   retrieval workflow here.
3. Run the Gate Checklist: version-check → behavioral probe → cite or mark unverified →
   conflict resolution.
4. Ship only claims that carry a citation or an explicit `[UNVERIFIED: reason]` label.

## Route Discovery to research leaves

Do not re-derive a retrieval workflow here. Load the matching leaf:

| Question | Route |
|---|---|
| Local code, architecture, definitions, traces, blast radius | `evidence-router` → Codebase Memory → JetBrains → Fovea |
| Current web facts, cited discovery | `codex-websearch` |
| Versioned library/API docs | `evidence-router` → Context7 (`resolve-library-id` → `query-docs`) |
| Package internals / source | `opensrc` |
| Pressure-test a claim against docs | `grill-with-docs` |

## Gate Checklist

1. **Version-check**: docs/package version vs the project's declared version.
2. **Behavioral probe**: verify with a direct run when the cost is low.
3. **Cite or mark unverified** (Iron Rule).
4. **Conflict resolution**: local code and tests > official docs/source > maintained examples > dated community posts.

## Red Flags

- Unfamiliar API used without citation or local precedent.
- Community answer conflicts with official docs.
- Docs version differs from package version.
- Agent invents options, flags, or imports.
- Research dump with no recommendation.

## Verification

- Key claims cite authoritative sources or are labeled unverified.
- Project/library versions considered.
- Recommendation is specific.
- External claims probed when cheap.

## Skill Result Contract

```xml
<skill_result>
  <skill>source-driven-development</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Sources consulted, version checks, probes</evidence>
  <artifacts>Citations or explicit unverified labels</artifacts>
  <risks>Unverified claims, stale docs, conflicting sources, or none</risks>
</skill_result>
```

## References

N/A — no reference files; routing and the gate checklist are fully specified in this file.
