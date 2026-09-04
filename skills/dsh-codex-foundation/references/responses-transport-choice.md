<!-- capsule-v2 -->
# Codex Responses transport choice — pick SSE or cached WebSocket per call from live preferences without putting compaction on the continuation chain

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how does a provider wrapper choose the per-call transport from live preferences while keeping plugin-owned compaction calls off the WebSocket continuation chain?

## OpenAICodexResponseRuntime.wrap/streamSimple/enterCompaction
**Path/Symbol:** src/responses.ts:325-362 OpenAICodexResponseRuntime (wrap 342-347, streamSimple 349-362, enterCompaction 331-339), sessionKey src/responses.ts:143-145; adapter wiring src/adapter.ts:148-157 and 181.
**Signature:** wrap(provider: Provider): Provider; private streamSimple(provider, model, context, options?): AssistantMessageEventStream; enterCompaction(sessionId: string | undefined): () => void.
**Data Shape:** compactionCalls is a Map<string, number> refcounting compaction marks keyed by sessionId ?? '<no-session>'; preferences arrive as a live () => ResponseApiPreferences read once per call. The adapter marks purpose === 'compaction' streams via enterCompaction and releases in finally.

### Decisive source
~~~ts
wrap(provider: Provider): Provider {
  return {
    ...provider,
    streamSimple: (model, context, options) => this.streamSimple(provider, model, context, options),
  }
}

private streamSimple(provider, model, context, options?) {
  const key = sessionKey(options?.sessionId)
  const compaction = (this.compactionCalls.get(key) ?? 0) > 0
  const preferences = this.preferences()
  if (compaction && preferences.useNativeCompaction) {
    return this.nativeCompactionStream(provider, model, context, options)
  }
  return this.standardStream(provider, model, context, options, !compaction && preferences.useWebSocketContextReuse)
}
~~~

**Flow:** adapter stream marks purpose → wrapper replaces only streamSimple on a spread copy of the provider → each call re-reads live preferences → compaction-marked session + useNativeCompaction routes to the native compaction request; otherwise delegation carries transport 'websocket-cached' when reuse is enabled and the call is not a compaction call, else 'sse'.
**Invariant:** the transport decision is made per call from current settings (no retained continuation state); a compaction mark forces the plain-SSE path even when context reuse is enabled; wrapping never alters the provider catalog, models, or OAuth flow; refcount release removes the key entirely at zero.
**Probe:** tests/response-runtime.spec.ts:67-76 (transports ['sse', 'websocket-cached'] around leaveCompaction) and 78-88 (live preference flips produce sse/websocket-cached/sse); executed via pnpm test -- tests/response-runtime.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.responses\\.OpenAICodexResponseRuntime\\.(wrap|streamSimple|enterCompaction)', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt the spread-wrap of exactly one provider method, the per-call preference read, and the refcounted purpose flag that keeps housekeeping streams off cached-continuation transports. Adapt the transport vocabulary ('websocket-cached'/'sse') and preference names to the target host. Omit Codex-specific native-compaction routing unless the target has an equivalent experiment flag. Coverage no_recorded_issue + metadata_match for src/responses.ts and tests/response-runtime.spec.ts; the graph inbound trace showed zero callers for enterCompaction but direct source reading found the true caller at src/adapter.ts:150 — source wins over graph.
