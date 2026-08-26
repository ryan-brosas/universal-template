<!-- capsule-v2 -->
# Bounded error-history ledger — how do you record per-server connection errors for UI display without unbounded memory or message flooding?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How are transport errors, stderr noise, and connect failures accumulated per server while staying bounded?

## Truncate to 1000 chars, keep last 100 entries, mirror latest into `server.error`
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`appendErrorMessage` :898–923; call sites: stdio onerror :735–743, onclose :745–751, stderr data :769–775, streamable-http/sse onerror :790–806/:833–849, connect catch :887–895).
**Signature:** `private appendErrorMessage(connection: McpConnection, error: string, level: "error" | "warn" | "info" = "error")`.
**Data Shape:** `connection.server.errorHistory: Array<{ message: string; timestamp: number; level }>` capped at 100; `MAX_ERROR_LENGTH = 1000` with literal `"...(error message truncated)"` suffix; `server.error` always mirrors the newest entry.

### Decisive source
```ts
// :899-903
const MAX_ERROR_LENGTH = 1000
const truncatedError =
    error.length > MAX_ERROR_LENGTH
        ? `${error.substring(0, MAX_ERROR_LENGTH)}...(error message truncated)`
        : error
```
```ts
// :916-922 — ring behavior by slice, plus display mirror
if (connection.server.errorHistory.length > 100) {
    connection.server.errorHistory = connection.server.errorHistory.slice(-100)
}
connection.server.error = truncatedError
```

**Flow:** every failure surface (transport onerror/onclose across all three transports, non-INFO stderr chunks, and the connectToServer catch which appends THEN rethrows) funnels into this one method → truncate → push with Date.now() + level → slice to last 100 → set `server.error`. Success clears only `server.error` (:880), never the history — history is an audit trail.
**Invariant:** append is the single choke-point: no call site mutates errorHistory directly; truncation happens BEFORE storage (bounded at rest), and the 100-cap applies after push (slice(-100)), so the newest entry can never be dropped.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts` describe `"Null safety improvements"` it `"should handle null client safely in disconnected connections"` (:599–639) exercises appendErrorMessage against a placeholder connection whose errorHistory starts undefined (lazy-init branch :906–908).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "appendErrorMessage errorHistory truncated", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → McpHub.appendErrorMessage Method src/services/mcp/McpHub.ts 898-923 (total: 1)
```

## Verdict
Adopt the bounded ledger verbatim (numbers included — they are the contract). Adapt level taxonomy if your UI renders warnings differently. Omit nothing.
