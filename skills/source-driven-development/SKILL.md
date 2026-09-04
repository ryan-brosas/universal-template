---
name: source-driven-development
description: "Use when shipping code that depends on unfamiliar libraries, external APIs, or framework behavior: cite the authoritative source or mark the decision unverified; route discovery itself to evidence-router."
invocation: internal
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
precedent), or mark the decision `[UNVERIFIED: reason]` explicitly, no citation and no
unverified label means the claim does not ship.

## When to Use / NOT

- **Use when:** shipping code that depends on unfamiliar libraries, external APIs, or
 framework behavior, any non-trivial external API, framework, or version decision.
- **NOT when:** doing the discovery itself, discovery belongs to the research leaves
 (`evidence-router`, `codex-websearch`, `opensrc`, `grill-with-docs`); this skill only
 enforces the rule at delivery time.

## Workflow

1. Identify every non-trivial external API, framework, or version decision in the
 change.
2. Route discovery to `evidence-router` instead of re-deriving a retrieval
 workflow here.
3. Run the Gate Checklist: version-check → behavioral probe → cite or mark unverified →
 conflict resolution.
4. Ship only claims that carry a citation or an explicit `[UNVERIFIED: reason]` label.

## Route discovery to the evidence owner

There is one evidence-routing owner: `evidence-router`. When an external
behavior materially affects the implementation, delegate source selection to
it (local code, Fovea, Codebase Memory, Context7, web, it picks the smallest
capable source). This skill enforces only the delivery-time rule: the claim
ships cited or labeled `[UNVERIFIED: reason]`.

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


## References

N/A, no reference files; routing and the gate checklist are fully specified in this file.
