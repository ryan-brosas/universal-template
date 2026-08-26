<!-- capsule-v2 -->
# Multi-round-trip input_required driver — how does a client auto-fulfil embedded elicitation/sampling/roots requests and retry until complete?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When a request returns `input_required` with embedded input requests plus opaque `requestState`, what loop fulfils them against already-registered handlers and retries — with what caps, pacing, and timeout accounting?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/inputRequiredDriver.ts`: `runInputRequiredDriver` (:216-246+), `buildInputRequiredRetryParams` (:130-141), `partitionInputResponses` (engine :37-56), `sleep(ms, signal)` (:158-176), `linkedRoundAbort` (:183-200), defaults (:52-66: autoFulfill=true, maxRounds=10, REQUEST_STATE_ONLY_LEG_PACING_MS=250); wiring in `inputRequiredEngine.ts` (`_resolveNonCompleteResult` extension point).
**Signature:** `runInputRequiredDriver({config, method, originalParams, firstPayload, requestOptions, hooks:{dispatchInputRequest, retry}, signal?, flowStartedAt?}): Promise<unknown>`.
**Data Shape:** Retry params = `{...originalParams, inputResponses: this-round's bare responses, requestState: byte-exact echo}` on a FRESH request id. Round cap counts BOTH request legs and requestState-only (load-shedding) legs; the latter pace at 250ms since nothing else slows the loop.

### Decisive source
```ts
// Byte-exact echo: the opaque string is copied verbatim, never parsed.
...(requestState !== undefined && { requestState })
// flowStartedAt is when the ORIGINAL request was issued (not when the driver
// started): maxTotalTimeout bounds the whole flow, so the first wire leg
// counts against the budget too.
requestOptions.onprogress?.({ progress: round, message: `Fulfilling input required by '${method}' (round ${round})` });
```

**Flow:** response funnel sees non-complete result → engine partitions `inputResponses` from the RETRY leg (bare results accepted; wrapped `{method,result}` envelopes recorded as droppedKeys so the handler re-issues) → dispatch each embedded request to the registered handler under a per-round abort linked to the caller's signal (first failure cancels siblings) → build retry params → `retry()` uses the MANUAL primitive (`allowInputRequired` semantics — a further `input_required` resolves raw instead of recursing) → loop until complete or cap → cap exceeded ⇒ typed `InputRequiredRoundsExceeded` carrying `{rounds, lastResult}` for manual resume.

**Invariant:** The driver is a LAYER over the manual path, not a second wire mechanism — disabling auto-fulfill simply skips the module. No new timer system: per-leg timeouts ride existing knobs; maxTotalTimeout shrinks the budget passed to each leg. Embedded handlers get synthesized contexts where related send/notify THROW (no live peer request to relate to). Each round emits synthetic progress so resetTimeoutOnProgress watchdogs see liveness.

**Probe:** `packages/client/test/client/inputRequiredEngine.test.ts` (engine loop, partitioning, caps).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "runInputRequiredDriver partitionInputResponses buildInputRequiredRetryParams", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt driver-over-manual-primitive layering with linked round aborts and byte-exact state echo; adapt caps/pacing; omit the legacy server-side shim twin unless you serve MRTR to old clients.
