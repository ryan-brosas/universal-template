<!-- capsule-v2 -->
# Negative-case ladder — how do you pin an adapter's whole bad-input taxonomy in one probe, including the cases where the CORRECT answer is not an error?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you pin an adapter's entire bad-input behavior taxonomy from the client side — including the five cases where the correct answer is NOT an error?

## smoke-negative.mjs — five distinct correct behaviors for bad input
**Path/Symbol:** `scripts/smoke-negative.mjs` (whole, 59L).
**Signature:** `h.expectError(id, method, params, { code, messagePattern?, timeoutMs? })` for the reject cases; `h.expectResult` + shape assertions for the non-error cases; `h.notify` for the no-op case.
**Data Shape:** each case pins (method, bad input, expected behavior class): prompt/load with unknown sessionId → JSON-RPC error; cancel with unknown sessionId → notification (no response exists); delete with unknown sessionId → success; initialize with protocolVersion 999 → success with clamped version; session/list with cursor 'bogus' → success with a sessions array.

### Decisive source
```js
// Unknown session id: prompt and load must reject with invalidParams.
const p1 = await h.expectError(2, 'session/prompt',
  { sessionId: 'does-not-exist-xyz', prompt: [{ type: 'text', text: 'hi' }] },
  { code: -32602 })
// Relative cwd on load must reject with invalidParams.
const p3 = await h.expectError(4, 'session/load',
  { sessionId: 'does-not-exist-xyz', cwd: 'relative/path', mcpServers: [] },
  { code: -32602 })

// Cancel on an unknown session is a no-op notification.
h.notify('session/cancel', { sessionId: 'does-not-exist-xyz' })
await new Promise(r => setTimeout(r, 300))

// Delete on an unknown session is idempotent success.
const del = await h.expectResult(5, 'session/delete', { sessionId: 'does-not-exist-xyz' })
assert(JSON.stringify(del ?? {}) === '{}', `delete unknown session not idempotent: ${JSON.stringify(del)}`)

// initialize with an unsupported protocol version clamps to 1 (no error).
const init2 = await h.expectResult(6, 'initialize', { protocolVersion: 999 })
assert(init2?.protocolVersion === 1, `protocolVersion clamp=${init2?.protocolVersion}`)

// session/list with a bogus cursor degrades to the first page.
const list = await h.expectResult(7, 'session/list', { cursor: 'bogus' })
assert(Array.isArray(list?.sessions), 'session/list sessions not an array')
```

**Flow:** the ladder walks five DISTINCT behavior classes for bad input: (1) REJECT — unknown sessionId on prompt/load and relative cwd on load throw invalidParams (-32602); (2) NO-OP — cancel on an unknown session is a fire-and-forget notification with nothing to assert except a 300ms settle proving no crash; (3) IDEMPOTENT-SUCCESS — delete on an unknown session returns `{}` (the ACP-spec idempotency the delete capsule owns server-side); (4) CLAMP — an unsupported protocolVersion is silently clamped to 1 instead of erroring (lenient where the spec allows); (5) DEGRADE — a bogus list cursor falls back to the first page instead of erroring. The insight: "everything bad must error" is wrong — a robust protocol adapter chooses the behavior class per method, and the probe pins the CHOICE.
**Invariant:** each bad input maps to exactly one behavior class and the probe asserts the class, not just "no crash"; the no-op case still gets a settle window so a latent crash surfaces before close; expectError verifies the exact code (-32602), not merely that an error occurred.
**Probe:** `node scripts/smoke-negative.mjs` → `OK smoke-negative (dist <hash>; cases: unknown prompt/load, relative cwd, cancel no-op, idempotent delete, version clamp, bogus cursor)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "expectError invalidParams -32602 protocolVersion clamp bogus cursor idempotent delete smoke-negative", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-class taxonomy (reject / no-op / idempotent-success / clamp / degrade) as the checklist for any protocol adapter's negative testing — one probe, one ladder, every method's bad-input choice pinned. Adapt the specific codes and clamps to your spec. Omit nothing: the non-error classes are the ones teams usually forget to pin. Coverage caveat: zero prior leaf citations; complements acp-smoke-harness.md (expectError API) and session-delete-list-contract.md (server-side idempotency) with the client-side taxonomy.
