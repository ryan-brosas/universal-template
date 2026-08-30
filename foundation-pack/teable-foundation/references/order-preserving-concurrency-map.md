<!-- capsule-v2 -->
# Order-preserving bounded-concurrency map — what is the minimal correct parallel-for over an array?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do you bound concurrent async work while keeping result order and index integrity?

## mapWithConcurrency
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/map-with-concurrency.ts:mapWithConcurrency` (:1–18).
**Signature:** `mapWithConcurrency<T, R>(items: ReadonlyArray<T>, concurrency: number, mapper: (item:T) => Promise<R>): Promise<R[]>`.

### Decisive source
```ts
const results = new Array<R>(items.length);
let cursor = 0;
const workerCount = Math.min(Math.max(1, Math.floor(concurrency)), items.length);
const workers = Array.from({ length: workerCount }, async () => {
  while (cursor < items.length) {
    const index = cursor++;
    results[index] = await mapper(items[index]!);
  }
});
await Promise.all(workers);
return results;
```

**Flow:** N persistent workers pull the next index from a shared cursor (JS single-threaded ⇒ claim is atomic); results written BY INDEX into a pre-sized array; worker count clamped to [1, items.length]. Used by redrive target scans, monitor target inspection, and anomaly fetches.
**Invariant:** Results are order-preserving REGARDLESS of completion order because assignment is by claimed index, not push. A rejected mapper rejects Promise.all (fail-fast) — callers needing per-item isolation wrap their own try/catch inside mapper (the redrive does).
**Probe:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/map-with-concurrency.spec.ts:6` ("bounds concurrent work and preserves input order").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "mapWithConcurrency", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as-is (~18L, zero deps). Note the repo carries four near-twins (airtable-import, space-migration, record-history-cold) — port ONE canonical helper.
