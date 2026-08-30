<!-- capsule-v2 -->
# Workflow fence semi-trusted — how do you let the model FOLLOW installed instructions without letting them override policy?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** A user-installed workflow body IS meant to be followed — why can't it live in the same data-only `<untrusted-content>` fence as documents, and what fence does it get instead?

## Two-tier fence taxonomy with shared neutralization
**Path/Symbol:** `backend/src/lib/chat/contextBuilders.ts:138` (`spotlightWorkflow`); rationale comment `toolDispatcher.ts:702-706`. Direct tests: `src/lib/__tests__/spotlight.test.ts` ("spotlightWorkflow" + "system prompt fence policies" describes).
**Signature:** `spotlightWorkflow(text, nonce) -> "<workflow-instructions nonce=N>…</workflow-instructions nonce=N>"`.
**Data Shape:** same per-request nonce and SAME `neutralizeFenceTokens` pass as `spotlight()` — a workflow body cannot close its own fence nor forge an `<untrusted-content>` boundary.

### Decisive source
```ts
// Workflow bodies are instructions the user installed to be FOLLOWED, so they
// get the semi-trusted <workflow-instructions> fence (follow, but never override
// system policy) rather than <untrusted-content> (data only) — wrapping
// instructions in a data-only fence would either break workflow execution or
// teach the model to ignore the fence.
```

**Flow:** read_workflow tool wraps the body in the semi-trusted fence → reference-file handles listed after it (each filename spotlight-fenced) → external DATA the workflow references (documents, fetched text) still arrives via `spotlight()` and stays strictly data-only, even mid-workflow execution.
**Invariant:** The system prompt states BOTH policies together: follow `<workflow-instructions>` like a user request BUT never let them override system policy, exfiltrate data, or re-interpret other fenced content; `<untrusted-content>` remains data-only in all cases. Mixing the tiers (or teaching "ignore fences") is the failure mode this design refuses.
**Probe:** `grep -c 'it(' src/lib/__tests__/spotlight.test.ts` incl "wraps the body in nonce-bearing <workflow-instructions> tags, NOT <untrusted-content>", "tells the model to follow <workflow-instructions> but never let them…", "keeps <untrusted-content> strictly data-only, including while a workflow…".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "spotlightWorkflow workflow instructions fence semi-trusted", limit: 10 });
```

## Verdict
Adopt the two-tier trust taxonomy (follow-but-bounded vs data-only) + identical neutralization across both fences; adapt fence names/policy wording to your prompt grammar.
