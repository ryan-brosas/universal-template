<!-- capsule-v2 -->
# One-tab-per-call parallelism — how do concurrent skills share one CDP connection without racing the active session?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What is the concurrency unit that makes every CLI invocation safe to run in parallel?

## createTarget(background) → attach(flatten) → route via cdp(sessionId,…) → fire-and-forget closeTab
**Path/Symbol:** `skills/cdp/interaction-skills/lifecycle-readiness.md` (:19-36); `session.ts:_call` explicit-sid routing (:344-347); `repl.ts:cdp` global binding (:44); `gsearch` script end-to-end instance.
**Signature:** `cdp(sessionId: string, method: string, params: unknown): Promise<unknown>` ≡ `session._call(method, params, { sessionId })` — never touches `activeSessionId`.
**Data Shape:** each call owns `{ targetId, sessionId }`; cleanup is `session.closeTab(targetId, sessionId).catch(() => {})` in `finally`.

### Decisive source
```js
const t = await session.Target.createTarget({ url: 'about:blank', background: true })
const { sessionId } = await session.Target.attachToTarget({ targetId: t.targetId, flatten: true })
try {
  await cdp(sessionId, 'Page.enable', {})
  ...
} finally {
  session.closeTab(t.targetId, sessionId).catch(() => {})   // guaranteed cleanup, never blocks the return
}
```
Why the pointer must not be touched (from SKILL.md):
> `cdp(sessionId, method, params)` … does **not** call `session.use`, so the active-session pointer is untouched. The multi-tab primitive … so concurrent tabs never race `session.use`.

**Flow:** fresh background tab per invocation → attach with `flatten:true` (sessionId-on-message over the ONE shared WebSocket) → route EVERY page-scoped call by explicit sessionId → read results → best-effort close in finally.
**Invariant:** (1) There is exactly ONE active-session pointer per daemon; any helper that calls `session.use()` mid-flight mutates global state for all concurrent snippets — parallel code must go through explicit sessionIds only. (2) `flatten:true` is what makes one WS carry N sessions without nested envelopes. (3) Cleanup is fire-and-forget BY DESIGN: awaiting teardown would delay results and a close failure must never fail an already-successful scrape. (4) If you must temporarily drive the pointer (auto-attach instrumenters), save/restore it around the mutation and serialize such bursts through a promise queue (record-cross-tab.md's `enqueue`).
**Probe:** pattern instantiated in every skill script; deterministic probe: `grep -c "createTarget" skills/*/scripts/*` and confirm each pairs with a `finally { session.closeTab(...)` block.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "attachToTarget", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-call tab + explicit-session routing for ANY multi-tenant CDP/WebSocket bridge; adapt tab churn cost (pool if creation latency matters); omit at the cost of serializing everything through the single active pointer.
