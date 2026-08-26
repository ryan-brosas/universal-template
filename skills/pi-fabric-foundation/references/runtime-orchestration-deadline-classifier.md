<!-- capsule-v2 -->
# Orchestration deadline classifier — static regex + dynamic ref set decide how long a sandbox may live

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** a 120s executor timeout kills long agent fan-outs, but you cannot just raise the global timeout for everything — how do you grant the long deadline ONLY to programs that actually block on child agents?

## Connected graph-selected seam
**Path/Symbol:** `src/runtime/orchestration.ts` whole file (22L): `BLOCKING_ORCHESTRATION_REFS = {agents.run, agents.wait, agents.ask}` (:5-9), `isBlockingOrchestrationRef` (:11-12), `ORCHESTRATION_RE` (:18-19), `codeUsesOrchestration` (:21-22).
**Signature:** `codeUsesOrchestration(code: string): boolean` — pure static test over source text; `isBlockingOrchestrationRef(ref: string): boolean`.
**Data Shape:** none — boolean gates consumed by execution-service (`effectiveTimeoutMs`) and node-process-runtime (`minimumTimeoutMsForHostCall`).

### Decisive source
```ts
// Match blocking guest entry points as call sites (a trailing "("), and
// tolerate a single-level generic such as agent<{ items: string[] }>(...).
// agents.handoff is excluded because it only schedules work at the completed
// outer fabric_exec boundary.
const ORCHESTRATION_RE =
  /\b(?:workflow\.agent|agents\.(?:run|wait|ask)|council\.run|rlm\.query)\s*\(|(?<!\.)\bagent\s*(?:<[^<>]*>)?\s*\(/;
```

**Flow:** at execute() entry, `codeUsesOrchestration(options.code)` decides whether the WHOLE program starts with `orchestrationTimeoutMs = max(executor.timeoutMs, agents.timeoutMs)` or the plain executor timeout. Then per host call, `minimumTimeoutMsForHostCall` re-checks: literal refs against `isBlockingOrchestrationRef`, computed/aliased refs after `fabric.$call` unwrapping — so `const r = ["agents","run"].join(".")` still raises the deadline when invoked even though no literal appears in a call position.
**Invariant:** (1) Detection requires CALL-SITE syntax — trailing `\s*\(` — so comments (`// agents.run something`), strings (`"agents.run"`), and bare identifiers never trigger. (2) The negative lookbehind `(?<!\.)` excludes METHOD calls like `obj.agent("x")`, and identifiers like `userAgent(` / `worker(` fail the `\b` boundary — only the guest's global `agent(...)` / `workflow.agent(...)` match. (3) Single-level generics tolerated: `agent<{ items: string[] }>("x")` matches via `(?:<[^<>]*>)?`. (4) `agents.handoff` is deliberately EXCLUDED from BOTH planes because it never blocks — it schedules at the outer fabric_exec boundary (deferred-handoff contract); including it would hand every handoff program the long deadline for nothing. (5) Read-only agent verbs (list/status/spawn/create/tell) stay off both sets — fire-and-forget work must not extend deadlines. (6) Static detection is an OPTIMIZATION only; the runtime-side per-call extension is the safety net ("computed and aliased refs cannot fall back to the short executor timeout" — module comment IS the invariant).
**Probe:** `tests/orchestration.test.ts:7` ("classifies only host calls that wait for child agent turns" — handoff/spawn/status/demo false; run/wait/ask true), `:19` "detects workflow agent entry points", `:29` ("detects generic typed workflow agent calls"), `:35` "detects direct blocking agents calls", `:42` "detects council and rlm entry points", `:47` "ignores read-only and non-blocking agent calls", `:59` "ignores plain tool calls and property access", `:67` "ignores orchestration tokens that are not call sites". Deadline behavior end-to-end: `tests/execution-service.test.ts:627/:858/:721`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "codeUsesOrchestration isBlockingOrchestrationRef ORCHESTRATION_RE blocking", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-plane classifier (static whole-program scan + dynamic per-call ref set) with call-site-anchored regex; adapt the ref vocabulary. Porters get this wrong by matching bare tokens (comments/strings false-positive) or by forgetting the dynamic plane, which silently reverts computed agent calls to the short timeout.
