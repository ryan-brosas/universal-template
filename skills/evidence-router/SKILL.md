---
name: evidence-router
description: "Use when choosing where to get evidence for a coding question: route by need and host to the smallest capable evidence source — Fovea, Steroid/JetBrains, source/tests, reference repos, Codebase Memory, OpenViking, docs, or web — and stop when the named gap is closed."
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

## Workflow

1. Choose the primary route from the Routes table for the need.
2. Escalate one step only after naming the gap.
3. Record each finding (claim, source, call, date, confidence).
4. Stop when the evidence authority matches the claim and the specific uncertainty has been closed; otherwise report the open evidence gap.

## Routes (need + host)

| Need | Primary | Then | Notes |
|---|---|---|---|
| Orient the active Pi repository (feature location, neighborhoods, symbols, impact, changed-code context) | **Fovea** (`fovea_sketch` → `fovea_focus` → `fovea_dwell`) | the exact source windows it names | navigation/context, not correctness proof; skip when direct reading is cheaper |
| Exact semantic/type/call information (usages, inheritance, refactor safety, inspections) | **MCP Steroid / JetBrains** (`steroid_*`) | source | also the runtime lane: debugger, test runner, expression evaluation |
| Runtime behavior | tests / debugger / runtime evidence | — | the only proof of behavior |
| One selected inspiration repository | project-local `<project>/reference/<repo>/` | Fovea on that root, then source + tests | see `reference-driven-development` for the workflow |
| Rendered visual or runtime evidence from a live website (DOM, CSS, screenshots, behavior) | **web-reference** (bounded capture) | inspect the capture like source | capture is evidence; the current project stays the acceptance authority |
| Design inspiration with no named source yet | web discovery (`gsearch` / Exa) or a design tool catalog | `web-reference` on the chosen site | propose candidates, capture only the selected ones |
| Find which past/indexed project contains a pattern (cross-repo, cross-session) | **Codebase Memory** (`list_projects` → `search_graph` / `trace_path`) | activate the candidate under `reference/` and inspect with Fovea/source | persistent library, cold path; the graph is an index, not truth |
| Past decisions, failed attempts, lessons, recurring edge cases | **OpenViking** (`memsearch` / `memgrep` / `memread`) | durable notes | experience memory — not a second copy of local source |
| Current library/API docs | official docs / **Context7** (`resolve-library-id` → `query-docs`) | vendored source | only when the question depends on current docs |
| Current external fact (versions, advisories, upstream changes) | **Exa** / a discovered read-only fetch | upstream source | cite what you actually opened |
| GitHub repository overview | DeepWiki (index → page) | the repository itself | bounded overview only |

Model opinions are not evidence routes. A model *processes* evidence; its
output is reasoning, load-bearing only after verification against source/tests. Needing different or stronger reasoning is
an execution decision (`skills/execution-router`), resolved mechanically by
`skills/model-resolution`.

## Escalation rule

Escalate one step only after naming the gap ("Fovea shows the neighborhood but
not the type hierarchy" → Steroid). Never run two routes for the same need up
front. On non-Pi hosts Fovea may be absent — Codebase Memory or direct source
then covers orientation.

## Model consultation (not evidence)

When a step needs different or stronger reasoning, that is an execution and
model-resolution decision (`skills/execution-router` → `skills/model-resolution`),
not an evidence route. Verify model output against source/tests before relying
on it. Frontend visual claims need rendered/runtime verification — if no
visual verifier is configured, record that as a capability gap instead of
treating model review as proof.

## Evidence validity

Source and tests outrank every summary, graph, skill, or model opinion. A
graph is an indexed navigation snapshot; a model answer is advisory reasoning.
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
or model answer as correctness proof; routing model/provider selection through
this skill instead of execution-router; a claim with no source.

## Verification

Each routed question ends with either a closed named uncertainty (the evidence
authority matches the claim) or a named open gap. Load-bearing claims are
confirmed against actual source/tests/runtime before implementation.

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
