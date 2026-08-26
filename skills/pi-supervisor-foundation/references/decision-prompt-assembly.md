<!-- capsule-v2 -->
# Decision prompt assembly — what context makes an LLM judge done/steer/continue reliably?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How is the supervisor's user prompt structured so the model cannot sit on the fence, forget the goal, or miss its own past failures?

## buildUserPrompt (`src/core/prompt-builder.ts`)
**Path/Symbol:** `src/core/prompt-builder.ts:buildUserPrompt` (:10-65), `buildASISummary` (:68-137).
**Signature:** `buildUserPrompt(state, contextText, agentIsIdle, ineffectivePattern?): string`.
**Data Shape:** Sections in fixed order: DESIRED OUTCOME → AGENT STATUS (+reframe) → STRUCTURED CONVERSATION CONTEXT → INTERVENTION HISTORY (last 5, with ASI dumps) → ASI PATTERN SUMMARY → REMINDER of outcome → "respond with JSON only".

### Decisive source
```ts
const agentStatus = agentIsIdle
  ? `AGENT STATUS: IDLE — ... You MUST return "done" or "steer".
     Returning "continue" here means the agent stays idle forever.`
  : `AGENT STATUS: WORKING — the agent is actively processing.
     Only intervene if clearly off track.`;
// history shows only last 5 interventions:
state.interventions.slice(-5).map((iv,i) => {
  let entry = `[${i+1}] "${iv.message}"`;
  if (iv.asi && Object.keys(iv.asi).length > 0)
    entry += `\n    ASI {${Object.entries(iv.asi).map(([k,v]) => `${k}: ${JSON.stringify(v)}`).join(', ')}}`;
  return entry;
});
```
ASI pattern summary arms (:74-129): any ASI key appearing in ≥2 of the last 5 interventions ⇒ `Pattern seen Nx: "key"`; ANY value containing suspicious indicators (unverified/contradict/suspicious/fake/skip/manipulat/cheat/gaming/short-circuit) ⇒ require explicit proof before accepting done; ≥2 interventions with contradict/unverified values ⇒ "pattern of unreliable reporting".

**Flow:** outcome stated FIRST and REPEATED at the end (primacy + recency sandwich around volatile context); idle status FORBIDS `continue` explicitly; reframe guidance injected between status and context; intervention history bounded to 5 so prompts stay stable-size.
**Invariant:** (1) Idle ⇒ continue must be unreachable-by-instruction; this pairs with parser fallbacks. (2) The goal appears twice verbatim — a porter dropping either copy measurably weakens drift resistance. (3) ASI is free-form `{[key]: unknown}` but its POWER comes from cross-turn frequency counting done HERE, not in the LLM. (4) History window (5) and pattern threshold (2×) are independent knobs.
**Probe:** `tests/engine.test.ts` — `includes outcome and agent status` (:219), `shows WORKING status when agent is not idle` (:235), `includes ASI from previous interventions` (:283), `surfaces recurring ASI patterns in summary` (:309), `warns about verification failures in ASI summary` (:344), `detects suspicious keywords in ASI values` (:379).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "buildUserPrompt agentStatus intervention history ASI", limit: 8 });
```

## Verdict
Adopt section order, double-outcome sandwich, idle-forbids-continue clause, and the ASI pattern-summary arms. Adapt section titles to your host. Omit the exact suspicious-word list if you have a domain-specific gaming vocabulary — keep the mechanism.
