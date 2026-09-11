<!-- capsule-v2 -->
# ACP diagnostics plane — how do you log third-party protocol state without leaking `_meta` secrets, and wrap failures with stage context?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The bridge must log what the agent advertised at initialize (identity, capabilities, auth methods) and wrap every protocol failure with context — but agent payloads carry `_meta` extension fields that may hold secrets, and raw causes may hold sensitive messages. How do you build the diagnostic snapshot and error wrapper?

## Recursive `_meta` strip + fixed-stage error wrapper
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/acp-diagnostics.ts` — `createACPInitializationDiagnostic` (:3–30), `createACPBridgeError` (:32–50), `getErrorMessage` (:52–70), `stripMetadata` (:73–80); wiring `bridge/index.ts` :586–590 (snapshot after session creation), :137–141 / :225–229 / :293–297 (the three stage call sites), :175–181 (snapshot emitted as bridgeLog attrs).
**Signature:** `createACPInitializationDiagnostic({ initialization, sessionId }): Record<string, unknown>`; `createACPBridgeError({ stage, cause }): Error` with `stage: 'session initialization' | 'session cancellation' | 'prompt update stream'`.
**Data Shape:** snapshot = `{ protocolVersion, sessionId, agent: {name, version, title?} | null, capabilities: <agentCapabilities minus _meta>, authMethods: [{id, type}] }` — auth method `type` falls back to `'agent'` when the SDK variant lacks the field. Error = `new Error(stage-only or stage+causeMessage)` with `error.cause = cause` always set.

### Decisive source
```ts
// acp-diagnostics.ts:73–80 — the whole secret-hygiene rule is this recursion
function stripMetadata({ value }: { value: unknown }): unknown {
  if (Array.isArray(value)) {
    return value.map(item => stripMetadata({ value: item }));
  }
  if (value == null || typeof value !== 'object') return value;
  const result: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    if (key !== '_meta') result[key] = stripMetadata({ value: item });
  }
  return result;
}
```

**Flow:** after a session is created (not at initialize — the sessionId comes from the created session), the bridge snapshots the initialization response through the strip and emits it once as an info bridgeLog under subsystem `acp.protocol` with the snapshot as attrs. Every failure on the three protocol stages goes through `createACPBridgeError`: session initialization (ensureSession catch), session cancellation (cancellation notification failure), prompt update stream (stream consumption error, after the raw-drain flush). The wrapper extracts a message from Error instances, `{message: string}` shapes, or bare strings; anything else (e.g. `{code: 'ECONNRESET'}`) yields stage-only text. The original cause is always attached as `error.cause` so upstream handlers can inspect it.
**Invariant:** nothing under a `_meta` key at any depth reaches the log attrs (the strip is recursive over objects AND arrays); the stage vocabulary is closed (three literals — callers cannot invent stages); cause preservation is unconditional (even message-less causes keep `error.cause`); message extraction never throws (unknown shapes degrade to undefined, not errors); the snapshot is emitted exactly once per session configuration (it lives in the same memoized block as the session fingerprint).
**Probe:** `bridge/acp-diagnostics.test.ts` (111L, 5 cases) — inline-snapshot pins the full stripped shape (agent `_meta` secret, capability `_meta` secrets at two depths, auth `_meta` all absent from output; title kept; auth type defaulted to 'agent'); four wrapper cases pin stage+cause message composition, cause identity preservation, `{message}`-shape extraction, and the stage-only degradation for message-less causes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createACPInitializationDiagnostic createACPBridgeError stripMetadata stage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the recursive `_meta` strip as the default hygiene pass for ANY third-party protocol payload you log — extension-metadata keys are the industry-wide secret channel (MCP, ACP, LSP all use `_meta`); adopt the fixed-stage error wrapper (closed vocabulary + unconditional cause preservation + degrade-to-stage-only messages) for protocol lifecycle errors so upstream triage never depends on cause shape. Adapt the stage set to your own lifecycle; omit the snapshot where you control both ends of the protocol. Coverage caveat: fully test-pinned (5 cases); the snapshot's once-per-fingerprint emission is deterministic-read-only (wiring site, not unit-tested).
