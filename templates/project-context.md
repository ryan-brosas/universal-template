---
purpose: Compact durable project context — only what is expensive to reconstruct from the repository itself.
updated: 2026-08-30
---

# Project Context — <project name>

Render 30–60 meaningful lines. Every line must survive this test:
*would reconstructing this from source, Git, manifests, or CI be expensive or
unreliable?* If not, leave it out — bootstrap detects it on demand.

## Intent

- [What this project is for and who it serves — the part not obvious from code.]
- [The decision that shaped the architecture, if it constrains future work.]

## Non-obvious constraints

- [Intentionally unsupported platforms/behaviors, and why.]
- [Data ownership or boundary rules automation cannot infer.]
- [Deployment/operational constraints that differ from local behavior.]

## Decisions worth remembering

- [<decision> — because <reason>; rejected: <alternative>]

## Traps

- [Failure mode, cache/generation trap, or ordering rule that cost real time once.]

## Boundaries

- [What must never change without explicit human sign-off.]

---

Render rules:

1. Every claim traces to evidence (file, command output, or a stated user
   decision) or is marked `[NEEDS CLARIFICATION: reason]`.
2. Nothing machine-recoverable: no versions, commands, branch names, dirty
   state, dependency lists, CI file locations.
3. No global philosophy, routing, or tool ownership — global AGENTS owns that.
4. Refresh reconciles: preserve hand-written lines, update only stale claims.
