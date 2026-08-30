<!-- capsule-v2 -->
# Stdio graceful teardown ordering — why must subscription close-results precede the wire close, and who closes what?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Three teardown triggers exist (handle.close, instance-side channel close, wire onclose) — how do they compose without double-close or losing the graceful-close signal?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/serveStdio.ts`: `closeAll` (:771-790), `onInstanceClosed` (:502-509), wire `onclose` (:802-812), handle.close (:821-826), `started` gate (:814-819).
**Signature:** `closeAll(): Promise<void>` — idempotent via `closing` flag + phase check.
**Data Shape:** Teardown order: graceful listen results → pinned/probe instance close → wire close.

### Decisive source
```ts
const closeAll = async (): Promise<void> => {
    if (closing || state.phase === 'closed') return;
    closing = true;
    const current = state;
    state = { phase: 'closed' };
    // Stdio server-side graceful teardown: emit the empty `subscriptions/listen`
    // JSON-RPC result for every active subscription (the spec's graceful-close
    // signal) BEFORE the wire is closed, so the client distinguishes graceful
    // end from a transport drop.
    for (const result of listenRouter.teardownAll()) {
        await wire.send(result).catch(error => reportError(toError(error)));
    }
    if (current.phase === 'probe' || current.phase === 'pinned') {
        await current.instance.product.close().catch(error => reportError(toError(error)));
    }
    await wire.close().catch(error => reportError(toError(error)));
};
// handle.close() awaits started first: surface a failed start through onerror; close still resolves.
close: async () => { await started.catch(() => {}); await closeAll(); }
```

**Flow:** any of the three triggers flips `closing` and snapshots state → graceful per-subscription results (each send failure caught, never aborting the loop) → instance product close → wire close. Instance-INITIATED close (`channel.onclose → onInstanceClosed`) tears down the connection — unless that channel is the one being deliberately discarded (`discarding` guard). Wire-close path skips listen results (transport is gone) but still closes the instance.

**Invariant:** The graceful signal MUST be written before the transport dies or clients can't distinguish clean shutdown from crash. Every await in teardown catches independently — one failed leg never prevents the others. `handle.close()` waits for `wire.start()` to settle first so a start failure is reported through onerror while close STILL resolves.

**Probe:** `packages/server/test/server/serveStdio.test.ts` :798 ("teardown" describe), :113 in serveStdioListen.test.ts ("handle.close() emits one empty subscriptions/listen result per active subscription id"); :675+ (close racing the opening factory).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "closeAll teardownAll onInstanceClosed serveStdio", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt signal-before-transport-close ordering + independent per-leg error capture + single-flight teardown latch; adapt the signal framing to your protocol; omit subscription semantics (`listen-router.md`).
