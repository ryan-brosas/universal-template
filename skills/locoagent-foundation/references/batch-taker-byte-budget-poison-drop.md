<!-- capsule-v2 -->
# Byte-budgeted batch taking — how do you cap POST payload bytes without letting one unserializable item hang the queue forever?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the batching rule when both item count and cumulative JSON bytes are bounded, and what happens to items JSON.stringify cannot serialize?

## takeBatch with in-place poison removal
**Path/Symbol:** `src/cli/transports/SerialBatchEventUploader.ts`: `takeBatch` (:213-233).
**Signature:** `private takeBatch(): T[]` — splice-based; honors `maxBatchSize` and optional `maxBatchBytes`.
**Data Shape:** First item ALWAYS taken regardless of size; each subsequent item included only if `bytes + itemBytes <= maxBatchBytes`; itemBytes measured via `Buffer.byteLength(jsonStringify(item))`.

### Decisive source
```ts
while (count < this.pending.length && count < maxBatchSize) {
  let itemBytes: number
  try {
    itemBytes = Buffer.byteLength(jsonStringify(this.pending[count]))
  } catch {
    // Un-serializable items (BigInt, circular refs, throwing toJSON) are
    // dropped IN PLACE — they can never be sent and leaving them at
    // pending[0] would poison the queue and hang flush() forever.
    this.pending.splice(count, 1)
    continue
  }
  if (count > 0 && bytes + itemBytes > maxBatchBytes) break
  bytes += itemBytes; count++
}
return this.pending.splice(0, count)
```

**Flow:** count-only fast path when no byte budget; otherwise walk-and-measure, dropping poison items at their index, stopping before the first oversized follower.
**Invariant:** The head-of-line position can never hold an unsendable item — that would make drain spin forever and flush() never resolve. Oversized-but-serializable items still flow (alone in their batch) because the first item bypasses the size check.
**Probe:** `grep -n "Buffer.byteLength(jsonStringify(this.pending\[count\]))" src/cli/transports/SerialBatchEventUploader.ts` (`:223`), `grep -n "this.pending.splice(count, 1)" src/cli/transports/SerialBatchEventUploader.ts` (`:225`), `grep -n "poison the queue" src/cli/transports/SerialBatchEventUploader.ts` (`:211`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "takeBatch maxBatchBytes unserializable", limit: 5 });
```

## Verdict
Adopt measure-at-take-time byte accounting and in-place poison splicing. Adapt the budget source (config vs header limits). Omit the try/catch ONLY if your message type is statically JSON-safe.