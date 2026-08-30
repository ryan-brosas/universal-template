---
name: veda-lane
description: Use when the work calls for the optional host-side Veda lane (navigator-plan, reviewer, worker, or deep thinking) and the session should keep design.json and report.yaml under .veda/sessions.
disable-model-invocation: true
---

# Veda Lane

Veda is an optional host-side one-shot lane, never a clone dependency. When the host has the `veda` CLI, delegate planning, review, and hard-problem convergence to it; when it is absent, the assembly-line prompts (`/plan`, `/ship`) carry the same work without it.

## Core Principle

Veda is an optional host-side one-shot lane, never a clone dependency — and model routing is authoritative: load-bearing planning and high-risk review go to `claude-opus-4-6-thinking` via direct `agy`, cheap discovery goes to gemini via `veda`.

## When to Use / NOT

- Use when the host has the `veda` CLI and the work calls for a navigator-plan, worker, reviewer, or deep-thinking lane with `design.json`/`report.yaml` under `.veda/sessions`.
- NOT when `veda` is absent (the assembly-line prompts carry the same work) or for load-bearing planning (use direct `agy`).

## Workflow

1. `veda -S <task> sel add <paths...>` — build the context personas see (75k–125k tokens; slice only above budget).
2. Invoke the lane: `-p navigator-plan` (plan), `-p worker '<abs design.json path>'` (bounded slice), `-p reviewer` (P0/P1/P2 vs design), or `deep` (k parallel solvers, k× cost).
3. Parse the structured output (`report.yaml`, `review: pass/needs-fix`) — not the prose. Stop when the review passes or the result is honestly reported.


## Model routing (authoritative — do not substitute)

- Load-bearing planning / architecture / high-risk review → `agy --model claude-opus-4-6-thinking --mode plan` (direct `agy` CLI, NOT veda/gemini).
- Critique / follow-up → `agy --model claude-sonnet-4-6 --mode plan`.
- Cheap discovery / context curation → `veda` + gemini (`gemini-3.7-flash-*`, `gemini-3.1-pro-low`).
- `veda deep` (parallel solvers) runs on gemini and is only for "N independent attempts"; the final architecture decision still comes from claude-opus.

## Personas and commands

- `veda -S <task-name> sel add <paths...>` — build the context the personas see (quote globs). Keep 75k-125k tokens; slice only above budget.
- `veda -S <task-name> -p navigator-plan '<goal + position>'` — plan with a read-only architect persona; ends with a plan report. For load-bearing planning use `agy --model claude-opus-4-6-thinking --mode plan` (direct agy, not veda); cheap discovery uses gemini (see Model routing).
- `veda -S <task-name> -p worker '<absolute path to design.json> ...'` — delegate a bounded implementation slice; the worker ends with a `<worker_report>` parsed into `report.yaml`.
- `veda -S <task-name> -p reviewer 'Review the diff ...'` — review findings P0/P1/P2 against `design.json`; fix P0/P1 until `review: pass`.
- `veda -S <task-name> deep '<hard problem>'` — k parallel solvers + judge + verifier for genuinely hard plans. Reserve for architecture or opaque bugs; it costs k×.

## Rules

- **CRITICAL**: Pi Fabric's native `agents.run({ runner: "veda", ... })` is currently broken (pi-fabric pipes the prompt to stdin, but veda-ts 0.75.8 reads positionals only). Strictly use the `veda` CLI via shell execution as shown above.
- Reuse one `-S` session name across plan, worker, and review so `design.json` and `report.yaml` stay together under `<project>/.veda/sessions/<task-name>/`.
- `.veda/` is ignored runtime state; never commit it. Durable records stay in `.pi/work/`.
- Prompts use single quotes (double quotes evaluate backticks as command substitution). Never pipe veda with `2>&1`; read stdout (response) and stderr (progress) separately, or use `-o file.md`.
- The Driver validates call sites, maintains the station ledger, and owns every Schema-gated mutation; personas never write repo files.
- If a persona call fails or is unauthored (missing credentials), report it honestly and fall back to native execution instead of faking the result.

## Red Flags

Using `agents.run({ runner: "veda" })` (broken — pi-fabric pipes the prompt to stdin, veda reads positionals only); double-quoted prompts with backticks (bash command substitution); piping veda with `2>&1` (progress header garbles the response); committing `.veda/` runtime state; substituting the model routing table.

## Verification

`design.json` and `report.yaml` sit together under `<project>/.veda/sessions/<task-name>/`; worker runs end with a parsed `<worker_report>`; reviewer runs end with `review: pass`; failed/unauthored persona calls are reported honestly, not faked.

## Skill Result Contract

```
<skill_result>
  <skill>veda-lane</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>commands run, outputs inspected, artifacts produced</evidence>
  <artifacts>files written / commands run</artifacts>
  <risks>known risks, untested paths, or none</risks>
</skill_result>
```

## References

No reference capsules — the skill is self-contained.
