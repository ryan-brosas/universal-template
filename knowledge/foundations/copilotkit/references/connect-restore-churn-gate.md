<!-- capsule-v2 -->
# Connect-restore churn detection — when does a reconnect need a FULL state reset vs. preserving local messages?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** On every `connectAgent` call, how do you tell "fresh thread restore" (must clear messages/state and replay) from "same-thread churn re-connect" (must preserve local state and resume from the last event)?

## ThreadId-delta restore gate in connectAgent
**Path/Symbol:** `packages/core/src/core/run-handler.ts:RunHandler.connectAgent` (:327-419; marker `_lastConnectedThreadIdsByAgent` :169, restore key :197-211, gate :331-364).
**Signature:** `async connectAgent({ agent }: CopilotKitCoreConnectAgentParams): Promise<RunAgentResult>` with private `getConnectRestoreKey(agent): string`.
**Data Shape:** `Map<string, string|null>` keyed by `agent:<agentId>` for named agents; anonymous agents get a WeakMap-stable `anonymous:<n>` identity (`_anonymousAgentIds`, `_nextAnonymousAgentId`) so proxy instances share one marker.

### Decisive source
```typescript
const incomingThreadId = agent.threadId ?? null;
const restoreKey = this.getConnectRestoreKey(agent);
const isFreshRestore =
  incomingThreadId !==
  (this._lastConnectedThreadIdsByAgent.get(restoreKey) ?? null);
this._lastConnectedThreadIdsByAgent.set(restoreKey, incomingThreadId);

// Detach any active run before connecting ... unconditional — both fresh
// restores and churn re-connects need the previous socket torn down.
await agent.detachActiveRun();

// State reset + replay-cursor clear are gated on actually moving to a
// different thread. On same-thread churn, the local messages/state are still
// the right view of the thread, and the gateway can resume from
// `lastSeenEventId` instead of replaying the full history.
if (isFreshRestore) {
  agent.setMessages([]);
  agent.setState({});
  const cursorAware = agent as { clearReplayCursor?...; clearReconnectCursor?... };
  if (incomingThreadId) {
    cursorAware.clearReplayCursor?.(incomingThreadId);
    cursorAware.clearReconnectCursor?.(incomingThreadId);
  }
}
```

**Flow:** capture incoming threadId → compare against per-agent last-seen marker → ALWAYS detach the active run (unconditional teardown) → only on a threadId CHANGE: clear messages + state + replay/reconnect cursors so the gateway performs a full replay → same-thread churn keeps local view intact and lets the gateway resume from `lastSeenEventId` → re-apply core headers merged over per-agent headers, notify subscribers, connect.
**Invariant:** Treating EVERY connect as fresh forces full-history replay on every effect-dep churn / transient disconnect — the documented production bug amplified churn into duplicate event rows and intermittent "Message not found" toasts (:154-167 comment). The detach stays unconditional even while the reset is gated.
**Probe:** deterministic anchor `grep -n "_lastConnectedThreadIdsByAgent" packages/core/src/core/run-handler.ts` (:169 declaration, :335 comparison, :336 write). Direct vitest suites for RunHandler live in `packages/core/src/core/__tests__/` (schema/capability/ensureObjectArgs); this seam is exercised via runtime runner suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "connectAgent isFreshRestore clearReplayCursor detachActiveRun", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the threadId-delta gate plus unconditional-detach split. Adapt the restore-key derivation if your agents lack stable ids (WeakMap identity fallback is the pattern). Omit cursor clearing on churn paths — clearing there is what reintroduces the duplicate-replay bug.
