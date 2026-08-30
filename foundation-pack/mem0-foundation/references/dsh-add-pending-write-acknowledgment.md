<!-- capsule-v2 -->
# dsh-mem0 async write acknowledgment — how do you report a PENDING extraction to a model?

**Source:** mem0 Apache-2.0 `main@7e09615`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** What does the add path return when extraction runs server-side AFTER the HTTP call, and how must the response shape be normalized before rendering?

## Three-shape unwrap + pending detection
**Path/Symbol:** `integrations/dsh-mem0/src/formatting.ts` (`formatAddResult`, lines 50-69).
**Signature:** `formatAddResult(result: unknown): string`.
**Data Shape:** accepts (a) `MemoryLike[]` array, (b) `{ results: MemoryLike[] }` envelope, (c) single object; each item may carry `status?: "PENDING"` and `eventId` OR legacy `event_id`.

### Decisive source
```ts
const items = Array.isArray(result) ? result
  : ((result as { results?: MemoryLike[] } | null)?.results ?? (result ? [result] : []));
const pending = items.find((r) => r.status === "PENDING");
if (pending) {
  const id = pending.eventId ?? pending.event_id;   // SDK camel-cases keys; accept either
  return `Memory queued for background extraction${id ? ` (event ${id})` : ""}; it will be searchable shortly.`;
}
if (items.length === 0) return "Memory stored.";
return `Stored ${items.length} ${items.length === 1 ? "memory" : "memories"}:\n${formatMemoryList(items)}`;
```

**Flow:** unwrap to a list → scan for any `status === "PENDING"` row → if found render the queued line with the event id → else empty list renders "Memory stored." → else render count + numbered list via `formatMemoryList`.
**Invariant:** The async `/v3/memories/add/` endpoint returns `{ event_id, status: "PENDING" }` — extracted memories are NOT in this response. Report the write as QUEUED and never claim stored facts exist yet. The SDK camel-cases response keys (`event_id`→`eventId`) but older/OSS shapes may not — accept either key or the confirmation loses its id half the time.
**Probe:** `integrations/dsh-mem0/tests/formatting.test.ts` ("reports queued for the async PENDING response, with the event id", "unwraps a { results: [...] } envelope", "handles an empty result" → exactly `"Memory stored."`) plus apply.test.ts's real-shape mock `{ eventId: "evt-123", status: "PENDING" }` asserting output contains "queued"+"evt-123" and NOT "No new distinct memory".
**Retrieve:** search_graph project `mnt-hdd-utopia-inspo-memory-mem0` query `formatAddResult` limit 4 → rank #1 is the near-tied cli/node twin `cli.node.src.output.formatAddResult` (output.ts 153-228); the target `integrations.dsh-mem0.src.formatting.formatAddResult` formatting.ts 50-69 sits at rank #2 within the same page — ROUTE BY QUALIFIED NAME (tied-twin precedent).

## Verdict
Adopt the three-shape unwrap, the PENDING-first branch with dual-key event-id tolerance, and the honest "queued ≠ searchable" wording (pair it with an anti-verification instruction in the tool description). Adapt the copy and list rendering. Omit nothing — this is the whole write-acknowledgment contract.
