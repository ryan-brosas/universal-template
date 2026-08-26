<!-- capsule-v2 -->
# Advisor delivery — severity alone is not enough

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi`. **Path:** `packages/coding-agent/src/advisor/advise-tool.ts`. **Question:** When should automated review advice interrupt, wait, or be preserved for the user?

## Source contract
**Path/Symbol:** `advise-tool.ts:isInterruptingSeverity` (74–76), `isAdvisorInterruptImmuneTurnActive` (81–88), `resolveAdvisorDeliveryChannel` (118–137).
**Signature:** delivery returns `"aside" | "steer" | "preserve"`.
**Data Shape:** severity (`nit | concern | blocker`), streaming/aborting state, user-interrupt suppression (`autoResumeSuppressed`), terminal-answer state (`terminalAnswerNoQueuedWork`), immune-turn fence.

### Decisive source
```ts
if (opts.preserveOnly && !opts.streaming) return "preserve";
if (!isInterruptingSeverity(opts.severity)) return "aside";
if (opts.autoResumeSuppressed && (opts.aborting || !opts.streaming)) return "preserve";
if (opts.terminalAnswerNoQueuedWork && opts.severity !== "blocker" && !opts.streaming && !opts.aborting)
  return "preserve";
if (opts.interruptImmuneTurnActive && opts.severity !== "blocker") return "aside";
return "steer";
```

**Flow:** classify severity → preserve if idle/aborting after a user interruption → route nits as asides → steer concerns/blockers → downgrade repeat interruption during the post-interrupt immune-turn cooldown. Parking during an ACTIVE run strands advice (it never reaches the running agent) — the bug the streaming guard prevents; a `blocker` is exempt from BOTH the terminal-answer and immune-turn downgrades because it means the agent handed off broken work (#5628).

**Invariant:** a late blocker after a terminal answer still wakes the primary; a suppressed idle/aborting run never auto-resumes from advisor traffic.

**Probe:** direct `test/advisor/advisor.test.ts:5228–5350` checks nits, terminal concerns versus blockers, immune turns, and post-interrupt streaming. Coverage caveat: tests excluded from graph index by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(isInterruptingSeverity|isAdvisorInterruptImmuneTurnActive|resolveAdvisorDeliveryChannel)$", limit: 8, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.advisor.advise-tool.resolveAdvisorDeliveryChannel" });
```

## Verdict
Adopt ordered delivery-channel resolution with blocker exemptions over suppression windows; adapt severities and channel effects to host; omit advisor-loop telemetry plumbing unless porting the full review loop.
