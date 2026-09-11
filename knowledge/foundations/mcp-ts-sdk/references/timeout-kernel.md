<!-- capsule-v2 -->
# Progress-aware timeout kernel — how do per-request timeouts, progress resets, and a hard total cap coexist on one correlation map?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should request correlation timeouts be structured so streaming progress keeps them alive but cannot starve them forever?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/protocol.ts`: `_setupTimeout` (:737-752), `_resetTimeout` (:754-770), `_cleanupTimeout` (:772-778), `_onprogress` reset path (:1164-1191, conditional reset :1177-1179), `_timeoutInfo` map (:566).
**Signature:** `_setupTimeout(messageId, timeout, maxTotalTimeout: number|undefined, onTimeout, resetTimeoutOnProgress=false)`; `_resetTimeout(messageId): boolean` (throws when the total cap is hit).
**Data Shape:** Per-message `TimeoutInfo {timeoutId, startTime, timeout, maxTotalTimeout?, resetTimeoutOnProgress, onTimeout}` keyed by numeric message id; progress tokens ARE the originating request ids.

### Decisive source
```ts
private _resetTimeout(messageId: number): boolean {
    const info = this._timeoutInfo.get(messageId);
    if (!info) return false;
    const totalElapsed = Date.now() - info.startTime;
    if (info.maxTotalTimeout && totalElapsed >= info.maxTotalTimeout) {
        this._timeoutInfo.delete(messageId);
        throw new SdkError(SdkErrorCode.RequestTimeout, 'Maximum total timeout exceeded', {
            maxTotalTimeout: info.maxTotalTimeout, totalElapsed });
    }
    clearTimeout(info.timeoutId);
    info.timeoutId = setTimeout(info.onTimeout, info.timeout);   // restart the SHORT timer
    return true;
}
```

**Flow:** request with `resetTimeoutOnProgress` → short timer armed (+ optional absolute cap) → each progress notification for that token resets the short timer UNLESS elapsed ≥ maxTotalTimeout ⇒ cleanup of response+progress handlers and timeout state, then the stored error is delivered to the response handler → normal completion deletes all three maps' entries together.

**Invariant:** The short timeout is restarted, never extended — an adversarial peer spamming progress cannot push total latency past `maxTotalTimeout` (measured from FIRST send, not last progress). Cap-exceeded is a thrown typed error funneled through the caller's handler (not a silent drop). Unknown progress tokens surface as errors rather than being ignored.

**Probe:** `test/client/protocol.test.ts` pins per the existing protocol capsule ("asserts −32020 on header mismatch, verifies timeout resets on progress notifications") — direct line-range re-pin queued as a pass-3 target below.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "_setupTimeout _resetTimeout _onprogress maxTotalTimeout", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt restart-not-extend resets over an absolute cap for any long-running correlated call; adapt error taxonomy; omit the progress-token-as-request-id coupling if your transport separates them.
