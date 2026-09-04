<!-- capsule-v2 -->
# Canonical-JSON Idempotency Key — how does payload key order become irrelevant to dedup?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you derive a stable task idempotency key from `(task, payload)` so identical data always dedups regardless of insertion order?

## Sorted-keys recursive stringify + 128-bit truncated SHA-256
**Path/Symbol:** `packages/typescript-sdk/src/internal/idempotency.ts` — `generateIdempotencyKey` (:13–21), `canonicalStringify` (:27–46).
**Signature:** `generateIdempotencyKey(task: string, payload: unknown): Promise<string>` (32-char lowercase hex); `canonicalStringify(value: unknown): string`.
**Data Shape:** hash input = canonical JSON of `{task, payload}`; digest truncated to first 16 bytes; Web Crypto (`crypto.subtle`) not `node:crypto` for Node/Bun/Deno/edge portability.

### Decisive source
```ts
if (Array.isArray(value)) {
    return `[${value.map(canonicalStringify).join(",")}]`;
}
if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const sorted = Object.keys(obj)
        .sort()
        .map((key) => `${JSON.stringify(key)}:${canonicalStringify(obj[key])}`)
        .join(",");
    return `{${sorted}}`;
}
return JSON.stringify(value);
```

**Flow:** `{task, payload}` → recursive sorted-key stringify (objects sorted, arrays order-PRESERVED) → TextEncoder → SHA-256 → slice(0,16) → hex.
**Invariant:** arrays are never sorted (`{xs:[1,2,3]}` ≠ `{xs:[3,2,1]}` as tests pin) — sorting applies to OBJECT keys only. Durable adapters override this default with engine execution identity (Temporal workflowId+activityId+attempt; langgraph prefixes `langgraph:` + `.slice(0,32)`), so the content hash is the DIRECT-mode default, not the universal one.
**Probe:** `packages/typescript-sdk/tests/idempotency.test.ts` (:17 same-input stability, :40 order-independence incl. nested objects, :52 array-order preservation, :71 `^[0-9a-f]{32}$` shape).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "generateIdempotencyKey canonicalStringify", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sorted-object-keys canonical stringify + truncation length + Web Crypto choice wholesale — every detail is test-pinned. Adapt the prefix scheme if your adapters need engine namespaces. Omit nothing; this is a complete portable contract.
