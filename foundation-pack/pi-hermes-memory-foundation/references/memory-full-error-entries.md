<!-- capsule-v2 -->
# memoryFullError entries envelope — return the current decoded entries WITH the capacity error so the model can fix it in one turn (#178)

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** When an add is rejected because memory is full, what should the error carry so a small model can recover without a second read round-trip?

## MemoryStore.memoryFullError
**Path/Symbol:** `src/store/memory-store.ts:memoryFullError` (:348–357); consumed by both overflow branches (:245 reject strategy, :323 fifo-evict-cannot-fit); type extension in `src/types.ts` (`target`, `usage`, `entry_count`, `entries?` fields on MemoryResult).
**Signature:** `private memoryFullError(target, contentLength: number): MemoryResult`.
**Data Shape:** `{ success: false, error, target, usage: "${current}/${limit} chars", entry_count: N, entries: string[] }` — entries are the DECODED texts (metadata comments stripped via `decodeEntry(...).text`), file order.

### Decisive source
```ts
const entries = this.entriesFor(target).map((raw) => this.decodeEntry(raw).text);
return {
  success: false,
  error: `Memory at ${current}/${limit} chars. Adding this entry (${contentLength} chars) would exceed `
       + `the limit. Replace or remove existing entries first (see the entries list below), then retry `
       + `this add — all in this turn.`,
  target,
  usage: `${current}/${limit} chars`,
  entry_count: entries.length,
  entries,
};
```

**Flow:** add overflows under `reject` strategy OR fifo-evict cannot make room even on an empty store → build the full envelope → the error text explicitly instructs "replace or remove … then retry this add — all in this turn" so the model treats the failure as a same-turn work order rather than a terminal refusal.
**Invariant:** metadata comments must NEVER leak into `entries` (`decodeEntry().text`, not raw) — leaking `<!-- created=… -->` strings back into the transcript taught models to write malformed metadata comments (#178 regression, asserted per-entry in tests). The envelope rides BOTH failure modes that produce `memoryFullError`; FIFO eviction that SUCCEEDS returns its normal evicted-entries shape instead.
**Probe:** `npx tsx --test tests/store/memory-store.test.ts` — "includes current entries in memoryFullError response under reject strategy" (:369, asserts `/see the entries list below/`, `usage` matches `/^\d+\/140 chars$/`, deep-equal decoded entries, and NO entry contains `<!--` or `created=`), "includes current entries in memoryFullError response when fifo-evict cannot fit the new entry" (:398, plus on-disk assertion that nothing was rotated). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "memoryFullError entry_count decodeEntry usage", limit: 5 })`

## Verdict
Adopt errors-as-work-orders: every capacity rejection carries the exact state needed to act in the same turn. Adapt field names to your result schema. Pair with `overflow-grace-window.md` (the deferral note appended when auto-consolidate is armed) and `memory-mutation-plan.md` (the atomic path the model should use to apply the fix).
