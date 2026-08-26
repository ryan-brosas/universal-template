<!-- capsule-v2 -->
# SSE snapshot broadcast — push-on-change run lists with torn-client cleanup and hot-reload safety

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you stream a periodically-refreshed collection (run list) to dashboard clients over SSE so clients only receive real changes, dead streams don't accumulate, and a dev-server reload can't corrupt state?

## Serialize-compare tick + enqueue-failure eviction + retire-before-replace
**Path/Symbol:** `packages/metaharness/src/server.ts` — `#tick`/`#broadcast` (240-260), `#sseResponse` (355-377), sync timer setup in `start` (207-224), teardown ordering in `stop` (226-238), globalThis instance retirement (755-768).
**Signature:** `#tick(): void` on a 2s `setInterval`; `#broadcast(frame: string): void`; SSE endpoint returns `new Response(ReadableStream, { headers: text/event-stream })`.
**Data Shape:** client set holds `{controller: ReadableStreamDefaultController<Uint8Array>, state: Open|Closed}`; frames are `data: <full JSON snapshot>\n\n` — the ENTIRE run-list JSON per change, not deltas.

### Decisive source
```ts
#tick(): void {
    this.#store.syncActive();
    const snapshot = JSON.stringify(this.#store.listRuns());
    if (snapshot !== this.#lastSnapshot) {       // push only on real change
        this.#lastSnapshot = snapshot;
        this.#broadcast(`data: ${snapshot}\n\n`);
    }
}
#broadcast(frame: string): void {
    const bytes = new TextEncoder().encode(frame); // encode once
    for (const client of this.#sse) {
        if (client.state === SseState.Closed) continue;
        try { client.controller.enqueue(bytes); }
        catch { client.state = SseState.Closed; this.#sse.delete(client); }  // torn-stream eviction
    }
}
// --hot re-evaluates the module in-place: retire the previous instance first,
// or its sync ticker and sqlite connection leak per reload.
await host.__metaharnessServer?.stop();
```

**Flow:** server start ⇒ discover + full reconcile (`syncAll`), then a 2s interval ticks: refresh all `running` rows from disk, serialize the run list, compare to the last frame, broadcast only when the string differs → each SSE connection registers its controller and immediately receives the current snapshot (no 2s wait) → broadcast encodes once and enqueues to every open client, evicting any whose stream throws → stop() closes controllers FIRST, then the HTTP server, then the store; dev reloads retire the old singleton through a globalThis handle before constructing the new one.
**Invariant:** full-snapshot frames keep clients trivially correct (no missed-event stitching) while serialize-compare keeps idle dashboards at zero traffic; a throwing enqueue must evict the client or the set grows forever; teardown order matters — close client streams before the server that owns them; exactly one live manager instance may hold the store/ticker.
**Probe:** exercised by every REST test via `manager.start()`/`stop()` lifecycle (`packages/metaharness/test/manager.test.ts:205-324` constructs/tears down repeatedly, including port 0). Coverage caveat: change-detection and eviction are source-read; lifecycle construction/destruction is indirectly test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "SseClient broadcast lastSnapshot sseResponse enqueue syncActive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any small ops dashboard over mutable state: poll-diff-broadcast loop, immediate initial frame per client, exception-driven eviction. Adapt interval, frame schema, and transport API; omit Bun-specific dev-reload codes (keep the retire-before-replace idea though — it is what prevents sqlite/timer leaks under any hot reloader).
