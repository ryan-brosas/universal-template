<!-- capsule-v2 -->
# Abort-error suppression ladder — which run/connect failures must NOT surface as user-visible errors?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** A user hits Stop mid-run (or navigation aborts a fetch) — how do you keep the resulting abort noise from popping error banners?

## Three-path abort classification in RunHandler
**Path/Symbol:** `packages/core/src/core/run-handler.ts:RunHandler.connectAgent` catch (:397-418), `createAgentErrorSubscriber.onRunErrorEvent` (:1282-1323), shared `emitError` helper (:1255-1270).
**Signature:** subscriber hook `onRunErrorEvent({ event }): Promise<void>`; local predicate `const isAbort = connectError.name === "AbortError" || connectError.message === "Fetch is aborted" || ...`.
**Data Shape:** terminal RUN_ERROR events carry an agent-supplied `code` (often `"abort"` on user stops) that is NOT standardized across agents — hence the client's own abort controller is the trusted signal.

### Decisive source
```typescript
// connectAgent catch:
const isAbort =
  connectError.name === "AbortError" ||
  connectError.message === "Fetch is aborted" ||
  connectError.message === "signal is aborted without reason" ||
  connectError.message === "component unmounted";
if (!isAbort) {
  await this._internal.emitError({ error: connectError,
    code: CopilotKitCoreErrorCode.AGENT_CONNECT_FAILED, context });
}
return { result: undefined, newMessages: [] };

// onRunErrorEvent (comment cites #5966 / #5812):
// A user-initiated stop makes the agent emit a terminal RUN_ERROR — often
// code "abort" — as its cancellation signal. That is expected, not a failure.
const runWasAborted = this._runAbortController?.signal.aborted === true;
if (runWasAborted || event?.code === "abort") {
  return;
}
```

**Flow:** three entry points classify failures — (1) connectAgent catches sync/async connect throws and string/name-matches the four known abort shapes; (2) the agent-error subscriber checks OUR abort controller FIRST (`runWasAborted`) before trusting the event's `code`, because only the client knows it initiated the stop; (3) `onRunFailed` still maps `AgentThreadLockedError` to its own dedicated error code so lock errors are never swallowed. Non-abort errors get structured context (`agentId`, `source`, `runtimeErrorCode` attached onto the raw error if absent).
**Invariant:** Prefer the abort controller over agent-supplied codes for stop detection; suppress ONLY cancellation-shaped failures — a locked thread or handler crash must still surface. Every suppressed path still returns the empty-result shape `{ result: undefined, newMessages: [] }` rather than throwing.
**Probe:** deterministic anchors `grep -n "signal is aborted without reason" packages/core/src/core/run-handler.ts` (:404) and `grep -n "runWasAborted" packages/core/src/core/run-handler.ts` (:1291). Runtime-side behavioral suites: `packages/runtime/tests/service-adapters/*/…language-model.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "onRunErrorEvent emitError AGENT_RUN_ERROR_EVENT AgentThreadLockedError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-signal rule (own controller first, event code second) and the explicit abort-shape list. Adapt the literal strings to your transport's abort vocabulary. Omit suppression of `AgentThreadLockedError`-class errors — they carry real state the UI needs.
