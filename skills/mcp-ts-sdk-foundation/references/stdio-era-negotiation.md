<!-- capsule-v2 -->
# Stdio era-negotiation state machine — how does one connection pin exactly one instance across probe, commit, and fallback?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A stdio connection can open as 2025 (`initialize`) or 2026 (enveloped request) or probe-then-decide — what state machine keeps the eras from mixing?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/serveStdio.ts`: `EntryState` union (:350-357), `classifyOpeningMessage` (:305-339), `processMessage` (:572-733), `connectInstance` (:511-533), `discardProbeInstance` (:539-570), strict-order pump (:738-769).
**Signature:** `serveStdio(factory: McpServerFactory, options?): StdioServerHandle`; state = `{phase:'opening'|'probe'|'pinned'|'closed', …}`.
**Data Shape:** Classification = `{kind:'legacy',reason:'initialize'|'no-claim'} | {kind:'modern',revision,classification} | {kind:'invalid-envelope'} | {kind:'unsupported-revision'}`.

### Decisive source
```ts
case 'modern': {
    if (isJSONRPCRequest(message) && message.method === 'server/discover') {
        if (state.phase === 'probe') { /* repeat probe: same optimistic instance, window STAYS OPEN */ ... }
        // Probe: answer from an optimistically built modern instance so the advertisement
        // reflects the real server definition, but do NOT pin the connection yet.
        const instance = await connectInstance('modern', opening.revision);
        if (isTornDown()) { await disposeLateInstance(instance); return; }   // close raced the factory
        state = { phase: 'probe', instance };
        ...
    }
    ...
    // The probe was followed by a modern request: the client committed to the modern era
    state = { phase: 'pinned', era: 'modern', instance: state.instance };
}
case 'legacy': {
    ...
    if (state.phase === 'probe') {
        // Probe-then-fallback: discard the probe; a FRESH legacy instance serves the handshake.
        await discardProbeInstance(state.instance);
        ...
    }
```

**Flow:** every inbound message queued and pumped in STRICT arrival order (factory construction is async; the queue absorbs overlap) → classify once → legacy opening pins a legacy instance (or rejects under `legacy:'reject'`) → discover probes WITHOUT pinning (repeated probes reuse the optimistic instance) → first non-discover enveloped request pins modern → enveloped NOTIFICATION during the window rides the probe without committing → after modern pin, a claim-less late `initialize` is answered with unsupported-version naming supported revisions (never fall back once confirmed).

**Invariant:** Every factory-built instance serves EXACTLY ONE era; ambiguity lives entirely in this entry. Factory may run twice (probe + fallback) so factories must be cheap/side-effect-free. After EVERY await in an opening arm, re-check `isTornDown()` — a close racing construction must neither resurrect state nor leak the instance. Errors escaping processMessage answer the request `-32603` (a throwing factory must not hang the client). Claim-less notifications during reject mode are dropped but keep the connection open for a modern opening.

**Probe:** `packages/server/test/server/serveStdio.test.ts` :134 (legacy default serve), :195 (modern opening), :256 ("server/discover probe window" incl. pipelined fallback initialize), :496 (reject mode), :531 (malformed/unsupported envelope entry-answered never pinned), :579 (factory/connect failure answered), :675 ("close racing the opening factory").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "serveStdio EntryState classifyOpeningMessage processMessage probe", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt one-classification-then-pin + optimistic-probe-with-open-window + teardown re-checks after awaits; adapt revision vocabulary; omit HTTP-entry analogs (`dual-era-entry.md` owns them).
