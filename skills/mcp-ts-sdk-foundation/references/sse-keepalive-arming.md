<!-- capsule-v2 -->
# SSE keep-alive arming — why invalid intervals disable rather than throw, and why 2^31 clamps instead of shrinking

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the contract for a keep-alive timer that must never crash a stream and never fire early?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/sseKeepAlive.ts` whole file (:1-15): `DEFAULT_SSE_KEEP_ALIVE_MS = 15_000`, `MAX_TIMER_DELAY_MS = 2 ** 31 - 1`, `armSseKeepAlive` (:7-15).
**Signature:** `armSseKeepAlive(intervalMs: number, onTick: () => void): ReturnType<typeof setInterval> | undefined`.
**Data Shape:** `undefined` = keep-alive disabled (caller must not clear anything); timer is UNREF'd.

### Decisive source
```ts
export function armSseKeepAlive(intervalMs: number, onTick: () => void): ReturnType<typeof setInterval> | undefined {
    if (!Number.isFinite(intervalMs) || intervalMs < 1) {
        return undefined;                       // NaN/Infinity/0/-1/0.5 ⇒ disabled, never thrown
    }
    const timer = setInterval(onTick, Math.min(intervalMs, MAX_TIMER_DELAY_MS));
    (timer as { unref?: () => void }).unref?.(); // optional-call: browser timers lack unref
    return timer;
}
```

**Flow:** caller passes configured interval → invalid values silently disable the feature → valid values arm an unref'd repeating tick, clamped to the max setTimeout/setInterval delay.

**Invariant:** CLAMP, never wrap or floor-to-1ms: Node's timers treat delays > 2^31-1 as 1ms — passing 2^31 through unclamped would busy-spin the event loop; `Math.min` turns overflow into "effectively off". Unref keeps a long-lived SSE stream from pinning process exit. The `(timer as {unref?}).unref?.()` pattern is the cross-runtime shim — feature-detect, don't branch on environment.

**Probe:** `packages/server/test/server/sseKeepAlive.test.ts` :10 (`it.each([0,-1,0.5,NaN,Infinity]) disables invalid delay` + zero timer count), :15 ("ticks at the configured interval"), :21 ("clamps overflowing delays instead of creating a 1ms timer" — 2^31 arms, no ticks in 60s).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "armSseKeepAlive DEFAULT_SSE_KEEP_ALIVE_MS MAX_TIMER_DELAY_MS", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt disable-on-invalid + clamp-not-wrap + unref for any long-lived stream heartbeat; adapt the default interval; omit the SSE frame format (streamableHttp plane).
