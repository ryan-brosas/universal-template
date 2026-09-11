<!-- capsule-v2 -->
# Execution trace V1 envelope — how do you record every tool call durably without leaking secrets or growing without bound?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what does the recorder guarantee about size, honesty, and outcome attribution for a persisted execution trace?

## Recorder + seal-time laundering + byte-budget shrink ladder
**Path/Symbol:** `src/audit/trace.ts:FabricExecutionTraceRecorder` (:438-613, `issueCall` :451, `seal` :472-612), handle `FabricExecutionTraceOperationHandle` (:376-436), sanitizer `sanitize` (:184-303); constants :3-18 (`FABRIC_EXECUTION_TRACE_MAX_BYTES = 512 * 1024`, MAX_RECORDED_OPERATIONS 2_048, MAX_NODES 8_192).
**Signature:** `recorder.issueCall(ref, args): Handle`; `handle.resolved(provider, action) / prepared(args) / succeed(result) / fail(stage, error, outcome?, result?)`; `recorder.seal(outcome, phases, _error?): FabricExecutionTraceV1`.
**Data Shape:** operation = `{type:"call", sequence, ref, provider?, action?, args, outcome, failureStage?, error?, result?}`; envelope `{kind:"pi-fabric.execution", version:1, outcome, phases[], operations[], counts{droppedValues,truncatedValues,redactedValues,droppedOperations}, error?}`.

### Decisive source
```ts
// seal(): unclosed operations inherit the RUN outcome; observed-aborted is
// re-labeled when the runtime's typed termination says timed_out
if (!operation.outcome) {
  operation.outcome = outcome === "timed_out" ? "timed_out"
    : outcome === "aborted" ? "aborted" : "failed";
  operation.failureStage ??= "invoke";
} else if (operation.outcome === "aborted" && outcome === "timed_out") {
  // Host calls observe an aborted bridge signal for both cancellation and
  // deadline expiry. The runtime's typed final termination is authoritative…
  operation.outcome = "timed_out";
}
```
```ts
// total-bytes shrink ladder, most-valuable-first (result → args → oldest op → phase)
for (let i = trace.operations.length - 1; traceBytes > FABRIC_EXECUTION_TRACE_MAX_BYTES && i >= 0; i--) { … delete operation.result; … }
for (let i = trace.operations.length - 1; traceBytes > FABRIC_EXECUTION_TRACE_MAX_BYTES && i >= 0; i--) { … operation.args = {}; … }
while (traceBytes > FABRIC_EXECUTION_TRACE_MAX_BYTES && trace.operations.length > 0) { …pop()… }
while (traceBytes > FABRIC_EXECUTION_TRACE_MAX_BYTES && trace.phases.length > 0)    { …pop()… }
```

**Flow:** `issueCall` snapshots the ref (byte-bounded, truncation counted) and projects args through the allowlist (see audit-allowlist-projection) → handle methods are ALL no-ops once `sealed` flips (late async completions cannot mutate history) → `seal` attributes outcomes to unclosed calls from the run-level verdict, rewrites non-success errors to stage templates ("Call failed during <stage>") EXCEPT the pi.bash invoke cause, folds every sanitization counter into `counts`, then shrinks under the 512 KiB envelope in value-order. Sanitizer drops sensitive/media/base64 values, replaces non-finite numbers/bigints/functions/cycles, sorts object keys, and caps depth/keys/array-length/nodes — every action increments a count.
**Invariant:** the serialized envelope NEVER exceeds `FABRIC_EXECUTION_TRACE_MAX_BYTES` (structural, not advisory) while operation ORDER survives (sequence strictly increasing, verified by the validator); every loss is visible in `counts` — a trace never silently omits; raw error text is never persisted except the single bash-cause carve-out; `isFabricExecutionTraceV1` rejects unknown versions, extra keys, circular structures, and hostile Proxies (try/catch → false).
**Probe:** `tests/audit-trace.test.ts:977` ("bounds large call traces while preserving operation order" — 500×16 KB commands stay ordered ≤ limit), `:996` ("enforces the total UTF-8 envelope bound with explicit drops"), `:1028` ("strictly ignores malformed and unknown trace versions" incl. hostile Proxy), `:977` region also pins bash-cause retention (:961).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricExecutionTraceRecorder seal issueCall truncatedIdentifiers droppedOperations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the recorder/handle split, seal-time outcome laundering, counted-loss discipline, and the result→args→operations→phases shrink ladder verbatim; adapt byte limits, stage names, and the bash-cause carve-out to your tool set; omit the QuickJS-bridge plumbing around the handles. Direct tests exist and are cited; graph coverage clean.
