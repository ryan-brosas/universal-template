---
name: model-router
description: "Use when a chosen role needs a backend/model resolved: discover currently available providers and models, filter by the role's capability requirements, rank with local preferences, select, and fall back gracefully — never hard-code a provider or model into the workflow."
disable-model-invocation: true
---

# Model Router

## Core Principle

**ROLE → REQUIRED CAPABILITY → BEST CURRENTLY AVAILABLE MODEL.** Never MODEL → WORKFLOW. Providers and models are runtime state: discover what exists now, filter by the role's hard requirements, rank with local preferences, and degrade gracefully. No provider ranking is permanent; capability is observed, not assumed.

## When to Use / NOT

- **Use when:** the effort router chose a mechanism (child, oracle, worker, reviewer...) that needs a backend/model resolved.
- **NOT when:** Main handles the task (no resolution needed); tiny tasks; choosing evidence sources (`evidence-router` owns that).

## Workflow (resolution policy)

1. **Discover** available providers/models (commands below). Inventory is runtime state — never trust a stale list, never freeze one into docs.
2. **Remove** unavailable or unauthenticated options.
3. **Filter** by the role's hard requirements: write capability, reasoning-level support, context size, tool access, runner compatibility.
4. **Rank** the survivors with local preferences: role fit, cost, subscription availability, speed, context, observed reliability, rate-limit pressure.
5. **Select** and execute.
6. **Fallback once** on provider failure: mark the option temporarily unavailable for this task, choose the next compatible option. No retry storms — never respawn the same request five times.

## Runtime discovery (verified commands; re-verify per installed version)

| Question | Command |
|---|---|
| Pi providers/models (context, thinking, images) | `pi --list-models [search]` |
| Pi provider readiness | `pi auth check --provider <name>` |
| Veda backends/aliases | `veda models [backend]` |
| Veda personas | `veda personas` |
| AGY inventory | `agy models` (when the CLI is present) |
| Backend CLIs present | `which claude codex droid gemini` |
| Fabric-native agent models | `agents.models()` inside a Fabric session (often empty — verify, do not assume) |
| Full stack report | `python3 ~/.agents/scripts/runtime-capabilities.py [--json] [--smoke]` |

`veda -b pi` bridges to whatever Pi has configured — the abstraction is `Veda → Pi backend → currently configured Pi provider/model`, so new Pi providers become usable lanes automatically. Runtime-verified mechanics (re-verify per installed version):

- Pi models via Veda are addressed as **`pi/<provider>/<model>`** — verified live: `veda -b pi -m pi/zro/deepseek-v4-flash-0731` answers; strings without the `pi/` prefix are rejected.
- Veda's Pi backend may not enumerate Pi's catalog (`veda models pi` has reported `models (unavailable)`) — discover with `pi --list-models`, pass an explicit `pi/...` model, and one-shot probe an unfamiliar lane.
- **Veda's global default model may be invalid on some backends** (observed: the configured default rejected by Codex+ChatGPT accounts) — always select an explicit backend-appropriate model per lane.
- **Installed ≠ authenticated**: a backend CLI can be present yet unauthenticated (observed: claude-code requiring `/login`). Readiness is also environment-scoped (`pi auth check` can report differently in a subprocess than the interactive shell) — verify in the environment the lane will run in.

## Facts vs preferences (never conflate)

- **Runtime facts:** provider exists; model exists; backend authenticated; reasoning level supported; context size; tools; runner works. Probed, machine-readable, ephemeral.
- **Local preferences:** "this model performed well on frontend work", "cheap enough for workers", "strong at architecture", "slow", "hits limits at noon". Observed, local, revisable — never encoded as universal facts, never written into global philosophy.

## Model profiles (small, local, optional)

When repeated evidence justifies it, keep preferences in a small local file (create it only when you have observations — the resolver works without it):

```yaml
# ~/.agents/config/model-profiles.yaml — preferences, not facts
# entries are fallback chains; resolve against `pi --list-models` / `veda models`
profiles:
  economy-worker:
    prefer: ["pi/<configured-cheap-provider>/<cheap-model>"]
  strong-reviewer:
    prefer: ["<current strong reasoning model>", "claude-code/opus"]
  frontend-critic:
    prefer: ["<current UI-capable reasoning model>", "<general strong reviewer>"]
  fast-investigator:
    prefer: ["pi/<fast-provider>/<fast-model>"]
```

Profiles are **fallback chains**: the resolver walks the list, skips unavailable options, and degrades to a generic strong candidate or to Main. Never fail a task because preferred option #1 is down.

## Diversity rules

- Provider diversity is useful when it reduces correlated failure or adds a genuinely different capability — not for its own sake. If one model handles everything reliably, use it.
- Same provider, different model is valid (cheap worker vs large-context investigator vs strong reviewer on one provider).
- Deep mode may mix models across solvers/judge when a problem is genuinely hard — never by default.
- Subscription balancing: simple signals only (current availability, known limits, observed failures). No quota prediction engines.

## Red Flags

- Hard-coded model slugs or provider rankings in workflows or philosophy. HARD-GATE (policy gate enforces).
- Failing a task because the preferred model is unavailable. HARD-GATE — fall back.
- Routing a tiny task through discovery/ranking ceremony. HARD-GATE.
- Treating a benchmark claim or price tag as capability evidence instead of observed outcomes.
- Confusing Veda aliases (local ergonomic config) with permanent model identities.

## Verification

The resolution is traceable: role → requirements → discovered options (with the discovery command output) → filtered/ranked choice → fallback used (if any). A one-shot probe (`veda -S <probe> -b <backend> -m <model> --no-tools`) verifies an unfamiliar lane before trusting it with real work.

## Skill Result Contract

```
<skill_result>
  <skill>model-router</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>discovery output, requirements, chosen backend/model, fallback path</evidence>
  <artifacts>resolution record for the audit log</artifacts>
  <risks>unverified lane, stale catalog, or none</risks>
</skill_result>
```

## References

No reference capsules — resolution policy is self-contained; lanes and CLI mechanics live in `veda-lane`, effort selection in `effort-router`.
