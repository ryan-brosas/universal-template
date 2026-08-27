<!-- capsule-v2 -->
# otel abort & error drain — closing every open span exactly once when a call dies mid-flight

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai`. **Question:** When streamText aborts or generateText throws, how do half-built span trees get terminated without leaks or double-ends?

## Path/Symbol
`packages/otel/src/open-telemetry.ts:onAbort` (:1392–1425) and `onError` (:1427–1473); legacy twins legacy-open-telemetry.ts `onAbort` (:1103–1130), `onError` (:1132–1162).

**Signature:** both take a single event; `onError(error)` receives EITHER the error object or an envelope `{callId, error}` and re-reads it defensively (`const event = error as { callId?: string; error?: unknown }; if (!event?.callId) return; const actualError = event.error ?? error;`).

### Decisive source
```ts
    for (const { span: toolSpan } of state.toolSpans.values()) {
      recordErrorOnSpan(toolSpan, actualError);
      toolSpan.end();
    }
    state.toolSpans.clear();

    if (state.inferenceSpan) {
      recordErrorOnSpan(state.inferenceSpan, actualError);
      state.inferenceSpan.end();
      state.inferenceSpan = undefined;
      state.inferenceContext = undefined;
    }
```
(:1436–1447 — error variant stamps the failure on EVERY live child before ending; abort variant runs the identical ladder with bare `.end()` and no status)

**Flow:** drain order is innermost→root in BOTH handlers: tools (Map) → inference → step → embeds (Map) → rerank → rootSpan.end() + cleanupCallState. Abort ends silently (spans keep whatever attributes they had); Error additionally sets ERROR status + exception event on each span via `recordErrorOnSpan`. The abort integration test drives a real streamText whose mock stream errors with DOMException AbortError on pull 4 and asserts ALL THREE spans (`invoke_agent`, `step 1`, `chat`) ended (:2361–2435).

**Invariant:** (1) Every end is followed by slot-clearing AND map clearing BEFORE root cleanup — a late event for this callId then finds no state and no-ops (silent-drop contract from the state machine capsule). (2) `onAbort` does NOT mark spans failed — an aborted call is not an errored call; porters who stamp ERROR on abort corrupt SLO dashboards. (3) The error envelope fallback (`event.error ?? error`) tolerates two dispatcher shapes; guard on `callId` presence, not instanceof. (4) Legacy onError omits the inference rung (legacy has no inference slot) and does NOT clear stepSpan's context var after end (:1141–1144 vs new :1401–1405) — cosmetic only because cleanupCallState drops the whole state. (5) Spans already ended earlier in normal flow are absent from state by then, so nothing is ever ended twice.

**Probe:** `grep -n "state.rootSpan.end();" packages/otel/src/open-telemetry.ts` → :1097/:1140/:1176/:1325/:1423/:1470. `grep -c "recordErrorOnSpan" packages/otel/src/open-telemetry.ts` → 9 (helper import+uses incl. per-family error stamps). Direct tests: open-telemetry.test.ts :1904 ("records error on root, step, and chat spans"), :2362 abort integration; legacy-open-telemetry.test.ts onError/onAbort describes (:928/:1006).

**Retrieve:** live-resolved rank-1 @pin:
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "OpenTelemetry cleanupCallState toolSpans end", limit: 3 });
// → otel OpenTelemetry.cleanupCallState 127-129 rank-1
```

**Verdict:** ADOPT — the drain ladder is the reusable contract; ordering and single-end discipline are the port hazards.
