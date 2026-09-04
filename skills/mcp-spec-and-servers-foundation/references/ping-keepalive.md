<!-- capsule-v2 -->
# Ping keepalive — what is the liveness probe contract, and why does the modern era have no ping page?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b6` (`docs/specification/2025-11-25/basic/utilities/ping.mdx`; absent from 2026-07-28 `basic/`); Codebase Memory `modelcontextprotocol`. **Question:** What must a receiver answer, when may a sender kill the connection, and how should a modern-era porter replace pinging?

## Either party sends `ping`; receiver MUST answer `{}` promptly; silence ⇒ stale
**Path/Symbol:** `docs/specification/2025-11-25/basic/utilities/ping.mdx` (whole page: overview :7–10; message format :12–27; behavior requirements :29–37; usage patterns :39–49; implementation considerations :51–58; error handling :60–64). Modern-era tree check: `docs/specification/2026-07-28/basic/` contains patterns/{cancellation,progress,subscriptions,...} — NO utilities/ping.mdx; the legacy-era page set (2024-11-05 … 2025-11-25) retains it under `basic/utilities/`.

**Signature:** request `{ jsonrpc: "2.0", id: "123", method: "ping" }` → response `{ jsonrpc: "2.0", id: "123", result: {} }` (empty result object).

**Data Shape:** zero params; empty-object result.

### Decisive source
```md
# 2025-11-25/basic/utilities/ping.mdx — behavior requirements
1. The receiver **MUST** respond promptly with an empty response:
   { "jsonrpc": "2.0", "id": "123", "result": {} }
2. If no response is received within a reasonable timeout period, the sender **MAY**:
   - Consider the connection stale
   - Terminate the connection
   - Attempt reconnection procedures
```
Implementation notes (same file): periodic pings SHOULD be configurable; excessive pinging SHOULD be avoided; timeouts treated as connection failures; multiple failures MAY trigger reset.

**Flow:** either side emits a plain `ping` request at a configurable cadence → receiver answers `{}` ASAP (no capability negotiation required — always available) → unanswered ping ⇒ sender MAY mark stale, terminate, or reconnect; repeated failures MAY escalate to connection reset.

**Invariants:**
1. **The response body is exactly `{}`** — returning null, omitting result, or echoing params fails strict clients.
2. **Ping is bidirectional and symmetric** — servers need liveness checks on clients too (e.g., before long task pushes).
3. **Modern-era porters should prefer transport-native health**: Streamable HTTP's request-scoped streams and stdio's process supervision make application-level pinging optional; treat this capsule as LEGACY-ERA surface and consult `deprecated-features-registry.md` before adopting any legacy utility in new code.
4. Timeout policy belongs to the SENDER; receivers never self-terminate for slow pings.

**Probe:** no runtime tests in the spec repo (docs-only); machine-checkable anchor: the `ping` method constant in schema.ts and its absence from the 2026-07-28 pattern pages. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "ping request empty result utilities", limit: 10, fields: ["name", "file"] });
```
(Live-verified form; the BM25 index surfaces the sep-automation bot's PingHandler — a DIFFERENT product's ping. The spec-page anchors above are reachable via `name_pattern` over schema sections, not free-text.)

## Verdict
Adopt prompt-empty-result answering if you implement ANY era's ping; adapt cadence/timeout to your network; in modern-era code OMIT application pings in favor of transport-level liveness unless serving legacy peers — record that choice against the deprecation registry.
