<!-- capsule-v2 -->
# ACP cold-restoration negotiation — how do you restore a stopped session without ever fabricating a fresh conversation?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When a replacement bridge must reattach to an existing agent-side conversation, how do you negotiate resume-vs-load, keep replayed history out of the new stream, and report which method won?

## Capability-gated restoration with history suppression
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/session-lifecycle.ts` — `resolveACPSessionRestorationMethod` (:7–30), `restoreACPBridgeSession` (:32–83); host-side twin `restoreColdACPSession` in `acp-v1-harness.ts:873–955`; terminal marker in `bridge/index.ts:183–204`.
**Signature:** `resolveACPSessionRestorationMethod({initialization, harnessId}): 'resume' | 'load'`; `restoreACPBridgeSession({agent, initialization, sessionId, cwd, mcpServers, meta, harnessId, setHistoricalUpdatesSuppressed, discardCapturedHistory}): {method, response}`.
**Data Shape:** capability probe reads loosely-typed `agentCapabilities.sessionCapabilities.resume` (present and not false ⇒ resume) else boolean `agentCapabilities.loadSession === true`; otherwise throws.

### Decisive source
```ts
// session-lifecycle.ts:16–29 — fail CLOSED: no advertised capability ⇒ no fresh session
if (sessionCapabilities?.resume != null && sessionCapabilities.resume !== false) return 'resume';
if (initialization.agentCapabilities?.loadSession === true) return 'load';
throw new HarnessBridgeCapabilityUnsupportedError({ harnessId,
  message: 'Cold ACP session restoration requires the agent to advertise sessionCapabilities.resume or loadSession; a fresh unrelated ACP session will not be created.' });
// :60–82 — suppression window wraps ONLY the restoration request
setHistoricalUpdatesSuppressed({ suppressed: true });
try {
  const response = method === 'resume' ? await agent.request(...session.resume, request)
                                       : await agent.request(...session.load, request);
  discardCapturedHistory();          // drop raw history captured during replay
  return { method, response };
} finally {
  setHistoricalUpdatesSuppressed({ suppressed: false });
}
```

**Flow:** replacement bridge initializes → resolve method from ADVERTISED capabilities (resume preferred over load) → suppress semantic session updates + capture raw stream → send resume/load → at the RESPONSE boundary discard all captured raw history and un-suppress (only post-restoration updates reach the turn) → the notification handler double-filters (`params.sessionId !== recoveredSessionId` + suppression flag) → host side `restoreColdACPSession` captures the negotiated method by listening for the RAW `acp-session-restored` event and settles only on finish/error/close; missing method ⇒ error. The bridge then emits finish `{unified:'stop', raw:'acp-session-restored'}` so the restoration slice itself has a well-defined terminal.
**Invariant:** restoration is fail-closed — absence of both capabilities throws rather than silently starting an unrelated session; replayed history must never enter the consumer's event stream (suppression + response-boundary discard); the negotiated method must be observed, never assumed.
**Probe:** direct tests `packages/harness-acp/src/v1/bridge/session-lifecycle.test.ts:21–62` (order assertion `suppressed:true → request:session/resume → discard → suppressed:false`), :64–144 (load fallback: zero semantic AND raw historical updates survive; post-response update flows), :146–171 (neither capability ⇒ HarnessBridgeCapabilityUnsupportedError); `acp-harness.test.ts:1880–2060` (host observes `restoration:{method:'resume'}` persisted into next stop state).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "restoreACPBridgeSession resolveACPSessionRestorationMethod acp-session-restored coldRestorationMethod", limit: 10 });
```

## Verdict
Adopt capability-negotiated restoration with a suppression window that discards replayed history AT THE RESPONSE BOUNDARY; adapt the two-method ladder to your protocol's session verbs; omit the specific ACP capability field names. Caveat: none — both sides (bridge negotiation, host observation) are unit-pinned.
