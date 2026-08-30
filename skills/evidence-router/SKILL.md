---
name: evidence-router
description: "Use when choosing where to get evidence for a coding question: route by need and host to the smallest capable source — Fovea, Steroid/JetBrains, source/tests, reference repos, Codebase Memory, OpenViking, docs, web, or Veda — and stop when the gap is closed."
disable-model-invocation: true
---

# Evidence Router

Route by NEED + HOST to the smallest capability that closes the gap. Pick ONE
primary route per question, escalate only after naming the gap, and stop when
evidence is sufficient.

## Core Principle

Pick one primary route per need, escalate only after naming the gap, and stop
when evidence is sufficient. Connected is not mandatory: never query a system
merely because it is reachable.

## When to Use / NOT

**Use** — deciding where evidence for a question should come from; closing a
named gap after the first route came up short.

**NOT** — as a ceremony. Do not walk every route per task; do not run a fixed
retrieval chain; if direct source already answers the question, stop.

## Routes (need + host)

| Need | Primary | Then | Notes |
|---|---|---|---|
| Orient the active Pi repository (feature location, neighborhoods, symbols, impact, changed-code context) | **Fovea** (`fovea_sketch` → `fovea_focus` → `fovea_dwell`) | the exact source windows it names | navigation/context, not correctness proof; skip when direct reading is cheaper |
| Exact semantic/type/call information (usages, inheritance, refactor safety, inspections) | **MCP Steroid / JetBrains** (`steroid_*`) | source | also the runtime lane: debugger, test runner, expression evaluation |
| Runtime behavior | tests / debugger / runtime evidence | — | the only proof of behavior |
| One selected inspiration repository | project-local `<project>/reference/<repo>/` | Fovea on that root, then source + tests | see `codebase-driven-development` for the workflow |
| Find which past/indexed project contains a pattern (cross-repo, cross-session) | **Codebase Memory** (`list_projects` → `search_graph` / `trace_path`) | activate the candidate under `reference/` and inspect with Fovea/source | persistent library, cold path; the graph is an index, not truth |
| Past decisions, failed attempts, lessons, recurring edge cases | **OpenViking** (`memsearch` / `memgrep` / `memread`) | durable notes | experience memory — not a second copy of local source |
| Current library/API docs | official docs / **Context7** (`resolve-library-id` → `query-docs`) | vendored source | only when the question depends on current docs |
| Current external fact (versions, advisories, upstream changes) | **Exa** / a discovered read-only fetch | upstream source | cite what you actually opened |
| Frontier model opinion (hard architecture, subtle debugging, high-risk review, UX reasoning) | **Veda** — Fabric `agents.run({runner: "veda", persona, model})` inside Pi; direct `veda` CLI otherwise | verify load-bearing findings against source/tests | advisory reasoning, never evidence by itself |
| GitHub repository overview | DeepWiki (index → page) | the repository itself | bounded overview only |

## Escalation rule

Escalate one step only after naming the gap ("Fovea shows the neighborhood but
not the type hierarchy" → Steroid). Never run two routes for the same need up
front. On non-Pi hosts Fovea may be absent — Codebase Memory or direct source
then covers orientation.

## Veda escalation policy

- **Normal code:** no Veda.
- **Hard architecture:** `navigator-plan` (navigator-chat for follow-ups).
- **High-risk review:** `reviewer` persona with a strong model.
- **Frontend/UI reasoning:** `frontend` / `frontend-auditor` persona — a
  Gemini-family model via AGY when useful.
- **Very hard ambiguous problem:** `veda deep` (multi-solver) when cost is
  justified.
- **Different provider perspective:** switch Veda backend/model family.

Selection is runtime-driven: `veda models [backend]`, `veda personas`,
`agy models`. Built-in personas are `navigator-plan`, `navigator-chat`,
`reviewer`, `worker`; anything else is a locally installed or custom persona —
never assume a persona or model exists without discovery. Never hard-code a
model claim: select from the installed catalog at run time. Inside Fabric, the
Veda runner is a one-shot headless child: no steering, no persistent actors, no
recursive Fabric.

A Veda opinion is not rendered-UI evidence and not a test result. Frontend
visual claims need actual runtime/render verification (browser, debugger,
screenshot); if no visual verifier is configured in the environment, record
that as a capability gap instead of treating model review as proof.

## Review routing (do not double-review by default)

| Change | Verification surface |
|---|---|
| Tiny local change | tests / lint only |
| Cross-file structural refactor | Fovea impact + tests |
| Type-sensitive refactor | Steroid semantic check + tests |
| High-risk architecture | Veda review + semantic/mechanical verification |
| Frontend visual change | Veda critique + actual rendered/runtime verification + tests/build |

## Evidence validity

Source and tests outrank every summary, graph, skill, or model opinion. A
graph is an indexed navigation snapshot; a Veda answer is advisory reasoning.
Capture provenance for external evidence (owner/repo, commit or branch,
license, retrieval date). Confirm exact source before load-bearing claims or
edits.

## Evidence Record

For each load-bearing finding record the claim, source tool, exact call/URL,
date, and confidence. Unknowns stay `[NEEDS CLARIFICATION: reason]`; no
source, no claim.

## Red Flags

Walking every connected system per task; querying a source because it is
connected rather than because a named gap needs it; treating a graph, corpus,
or Veda answer as correctness proof; hard-coding a model or persona claim
without runtime discovery (`veda models` / `agy models`); confusing model
review of UI with rendered verification; a claim with no source.

## Verification

Each routed question ends with either sufficient evidence (one primary source
answers, or two independent sources agree) or a named open gap. Load-bearing
claims are confirmed against actual source/tests/runtime before
implementation.

## Skill Result Contract

```
<skill_result>
  <skill>evidence-router</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>One primary route per need, named gaps, compact evidence records</evidence>
  <artifacts>Routed evidence ledger</artifacts>
  <risks>Duplicate retrieval, unverified model claims, or none</risks>
</skill_result>
```

## References

N/A — routing tables and validity rules are inline in this skill.
