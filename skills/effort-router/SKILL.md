---
name: effort-router
description: "Use when deciding how much agent effort and which execution mechanism a task needs: Main, focused child, bounded parallel workers, an alternate-model oracle, recursive decomposition, or a persistent actor — before any model or provider is chosen."
---

# Effort Router

## Core Principle

Three routers, three questions, kept separate: the **evidence router** decides WHERE knowledge comes from, the **effort router** (this skill) decides HOW MUCH and WHAT KIND of agent effort, the **model router** decides WHICH backend/model executes. The effort router chooses the mechanism only — provider and model selection happen after, in `skills/model-router`.

## When to Use / NOT

- **Use when:** a task looks heavy, uncertain, parallelizable, context-bound, or like it needs an independent perspective — decide the mechanism deliberately.
- **NOT when:** normal work — Main plus source plus tests is the default, and a router ceremony for a typo fix is itself a violation.

## Workflow

Stop at the first mechanism that closes the gap:

1. **Can Main solve it comfortably?** → Main. Done.
2. **Can the uncertainty be isolated?** → focused child (one subsystem, one reference repo, one bounded question).
3. **Multiple independent questions?** → bounded parallel workers (concurrency ceiling; each worker owns one question).
4. **Need another model/provider perspective?** → model oracle via the model router (`skills/model-router`): strong reasoning, independent context, advisory output.
5. **Relevant context still too large?** → recursive decomposition / RLM-style reduction — shrink the problem before spending model effort.
6. **Must responsibility persist?** → Actor — an explicit long-running responsibility watching its own trigger, outside the short-lived task path.

## Roles (capability requirements, never provider names)

| Role | Requires |
|---|---|
| MAIN | economical, fast, tool-capable, holds the session |
| WORKER | code competence, write access in its slice, cheap |
| REFERENCE-INVESTIGATOR | code comprehension, adequate context, read-only, cheap |
| REVIEWER | strong reasoning, read-only, independent context, high confidence |
| NAVIGATOR | strong planning reasoning, read-only, structured output |
| FRONTEND-CRITIC | UI/UX or multimodal reasoning ability — whichever currently available model has it |
| DEBUGGER | runtime/tool access, hypothesis discipline |
| SECURITY-REVIEWER | adversarial reasoning, read-only |
| SOLVER / JUDGE / VERIFIER | independent strong reasoning; diversity between them when the problem is hard |
| SUPERVISOR | orchestration reliability, budget discipline |

## Context isolation is a first-class reason

A child earns its cost by providing a **distinct context or responsibility** — not necessarily a different model. Main's model running on a bounded slice (one subsystem, one reference repo) is a valid, often ideal child. Same model, fresh context: valid.

## Pi children are not the Main model by default

When supported, a child Pi invocation may run a different configured provider/model than Main (cheaper workers, stronger reviewers, provider diversity, rate-limit spread, specialized models). Discover options at runtime (`pi --list-models`, `skills/model-router`); never assume child == Main.

## Red Flags

- Building the full multi-provider topology for a task that one Main pass handles. HARD-GATE.
- Rejecting a same-model child because it lacks a different model — judge it on context/responsibility distinctness.
- Choosing the model before choosing the mechanism.
- Skipping the evidence router: effort spent on the wrong question is waste.

## Verification

Record the chosen mechanism, the role, and the named capability requirements; the model-router resolution then traces from those requirements. If the task completed without escalation, record that too — no escalation is a valid outcome.

## Skill Result Contract

```
<skill_result>
  <skill>effort-router</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>mechanism chosen, role, capability requirements, stop reason</evidence>
  <artifacts>delegation/execution plan</artifacts>
  <risks>over-orchestration, missed isolation, or none</risks>
</skill_result>
```

## References

- `../model-router/SKILL.md` — capability-driven backend/model resolution for the chosen role
- `../evidence-router/SKILL.md` — the upstream question: where evidence comes from
- `../fabric-native-execution/SKILL.md` — the execution layers (core path, native children, Veda runner, Schema modes)
