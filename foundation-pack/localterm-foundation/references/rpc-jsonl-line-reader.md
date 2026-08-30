<!-- capsule-v2 -->
# JSONL RPC line reader — why not readline over a child's stdout?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** What breaks if you use Node's readline to consume an NDJSON RPC stream?

## LF-only splitter with waiter/queue handoff
**Path/Symbol:** `packages/server/src/pi-rpc-client.ts:RpcClient` (:7–81).
**Signature:** `nextLine(timeoutMs: number): Promise<string|null>`; `send(cmd)`; `close()`.
**Data Shape:** Internal buffer + `lineQueue` (early lines) + `lineWaiters` (pending reads); null resolves on close OR timeout; `\r` stripped for CRLF tolerance.

### Decisive source
```ts
// JSONL line reader over a child's stdout. Splits on `\n` only (RPC mode uses
// LF as the record delimiter; readline is non-compliant because it also splits
// on U+2028/U+2029, which are valid inside JSON strings).
```
```ts
nextLine(timeoutMs: number): Promise<string | null> {
    if (this.lineQueue.length > 0) return Promise.resolve(this.lineQueue.shift() ?? null);
    if (this.closed) return Promise.resolve(null);
    return new Promise((resolve) => {
      let settled = false;
      const waiter = (line: string | null): void => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        ...
        resolve(line);
      };
      const timer = setTimeout(() => waiter(null), Math.max(0, timeoutMs));
      this.lineWaiters.push(waiter);
    });
  }
```

**Flow:** stdout chunks accumulate → split on `\n` → each complete line resolves the OLDEST waiter or enqueues → close/error events drain waiters with null → read loop uses ≤1000ms timeouts so wall-clock deadlines stay checkable between lines.
**Invariant:** readline ALSO splits on U+2028/U+2029 — legal INSIDE JSON strings — so a tool result containing a line separator would be split into invalid JSON fragments and silently dropped by the parser (`catch { continue }`). The one-time `settled` latch makes a racing timeout+line benign. `close()` ends stdin then SIGKILLs after 2s as a last-resort reaper.
**Probe:** `packages/server/src/pi-rpc-client.ts:7–6` header comment pins the rationale; behavioral coverage rides the integration suites consuming this client (`tests/agent-runner.test.ts` runAgent suites exercise nextLine/send/close end-to-end through the fake pi).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "RpcClient nextLine JSONL U+2028", limit: 10 });
```

## Verdict
Adopt LF-only splitting for any JSON-lines protocol and the queue/waiter pump shape; adapt reaping delays. No dedicated unit suite — deterministic greps + integration coverage stand in (recorded caveat).
