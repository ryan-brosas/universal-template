---
name: veda-lane
description: Use when a task justifies a Veda lane (navigator-plan, reviewer, worker, or deep thinking) — probe availability at runtime, discover models with veda models, delegate via the Fabric Veda runner when supported or the direct veda CLI otherwise.
disable-model-invocation: true
---

# Veda Lane

Veda is an optional model-escalation lane, never a dependency. Probe the installed pair at runtime; delegate through Fabric's Veda runner when it works, else the direct `veda` CLI; when neither is available, the normal Pi path carries the work.

## Core Principle

Veda output is advisory. Probe availability instead of trusting claims (no hard-coded "broken" or "works" rules), select models/personas from the runtime catalog, delegate through the simplest supported path, and verify load-bearing conclusions against source/tests/runtime evidence.

## When to Use / NOT

- **Use when:** hard architecture, difficult debugging, high-risk review, frontend/design reasoning, an independent second opinion, or a very hard ambiguous problem justifies a stronger or different model family.
- **NOT when:** normal implementation (Veda is never mandatory); when unavailable — fall back to native execution and report honestly instead of faking a result.

## Workflow

1. **Probe once per session.** `veda --version` + `veda models` (installed backends and aliases) + `veda personas` (built-in vs locally installed). `python3 ~/.agents/scripts/runtime-capabilities.py` reports the whole stack including Fabric/Veda versions.
2. **Pick the lane by task.** `navigator-plan` (hard architecture), `reviewer` (high-risk review), `frontend` / `frontend-auditor` (UI/design — a Gemini-family model when the catalog offers one), `worker` (bounded delegated implementation), `deep` (multi-solver; k× cost, only for genuinely hard ambiguous problems).
3. **Select models from the runtime catalog only** — `veda models <backend>`, `agy models`. Never hard-code a slug: AGY-hosted Claude may or may not exist in the installed catalog; Claude `opus` rides the claude-code backend when installed.
4. **Delegate through the simplest supported path.** Prefer Fabric's `agents.run({ runner: "veda", persona, model })` — a one-shot headless child at the outer fabric_exec boundary (see the installed pi-fabric `docs/agents.md`, "Veda runner"). If the installed Fabric/Veda pair rejects it, fall back to the direct CLI and note the version pair — do not encode a temporary incompatibility as a permanent rule.
5. **Parse structured output** (`report.yaml`, `review: pass/needs-fix`, worker reports) — not prose.
6. **Verify load-bearing findings** against source/tests/runtime before acting on them.

## CLI mechanics (direct path; verified on veda 0.75.x)

- `-S <task>` isolates selection and conversation under `<project>/.veda/sessions/`; reuse one session across plan/worker/review. `.veda/` is ignored runtime state — never commit it.
- Quote prompts with single quotes (backticks inside double quotes execute as command substitution); read stdout and stderr separately, or use `-o file.md`.
- Built-in personas: `navigator-plan`, `navigator-chat`, `reviewer`, `worker`; anything else listed by `veda personas` is locally installed or custom — do not assume it exists elsewhere.

## Rules

- Veda is never mandatory and never runs for routine implementation.
- Advisory output: load-bearing conclusions require source/tests/runtime verification.
- Model and persona selection comes only from the runtime catalog (`veda models [backend]`, `veda personas`, `agy models` when present).
- Personas never write repo files outside their delegated slice; you validate and integrate. Failed or unauthenticated calls are reported honestly, never faked.

## Red Flags

- Hard-coding model slugs or "runner broken / runner works" claims instead of probing the installed pair. HARD-GATE.
- Invoking Veda for routine implementation, or making it a mandatory phase.
- Faking a persona result when a call fails or is unauthenticated. HARD-GATE.
- Committing `.veda/` runtime state.

## Verification

- Availability probed and recorded (versions, installed backends, personas).
- Structured outputs parsed where applicable (`report.yaml`, review status).
- Load-bearing findings verified against source/tests; fallback honestly reported when Veda is unavailable.

## Skill Result Contract

```
<skill_result>
  <skill>veda-lane</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>probe results, lane invoked, parsed outputs, verification notes</evidence>
  <artifacts>report.yaml / review findings / session artifacts under .veda/sessions</artifacts>
  <risks>unverified model claims, fabricated outputs, or none</risks>
</skill_result>
```

## References

No reference capsules — the skill is self-contained; routing policy lives in `evidence-router`.
