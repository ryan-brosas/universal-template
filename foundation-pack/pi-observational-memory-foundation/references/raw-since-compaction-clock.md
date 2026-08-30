<!-- capsule-v2 -->
# Raw-since-compaction clock — firstKeptEntryId rewinds the counting boundary BELOW the compaction entry

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** Automatic compaction's trigger setting counts ledger-entry tokens — but from WHERE in an append-only ledger that just gained a compaction entry?

## The clock (`src/session-ledger/progress.ts`)
**Path/Symbol:** `progress.ts:113-118` (`findLastCompactionIndex`), `progress.ts:220-229` (`rawTokensSinceLastCompaction`), `progress.ts:16-43` (`entryIndexById` / `entryIndexForId`), `progress.ts:22-35` (`isSourceEntry`, `rawTokensAfterIndex`).
**Signature:** `rawTokensSinceLastCompaction(entries): number`.
**Data Shape:** compaction entry carries `firstKeptEntryId?: string`; source entries = message/custom_message/branch_summary; memory + compaction entries are never counted.

### Decisive source
```ts
export function findLastCompactionIndex(entries: Entry[]): number {
	for (let i = entries.length - 1; i >= 0; i--) {
		if (entries[i].type === "compaction") return i;
	}
	return -1;
}

export function rawTokensSinceLastCompaction(entries: Entry[]): number {
	const compactionIndex = findLastCompactionIndex(entries);
	if (compactionIndex === -1) return rawTokensAfterIndex(entries, -1);   // no compaction ⇒ count whole ledger
	const firstKeptIndex = entryIndexForId(entries, entries[compactionIndex].firstKeptEntryId);
	if (firstKeptIndex === -1) return rawTokensAfterIndex(entries, compactionIndex);
	return rawTokensAfterIndex(entries, firstKeptIndex - 1);               // THE line
}
```

**Flow:** reverse scan for the last `type === "compaction"` → resolve `firstKeptEntryId` to a branch index via the id→index map → count raw tokens from one index BEFORE that id. Missing id resolves to `-1` and degrades to counting-from-compaction-entry. No compaction ever ⇒ whole-ledger raw total.

**Invariant:** The counting boundary is deliberately `firstKeptIndex − 1`, NOT the compaction entry itself. pi keeps the first kept turn IN context after compaction, so entries at indexes `[firstKeptIndex …]` are live tail; the compaction entry sits after them in append order, meaning a porter who counts "after the compaction index" would wrongly EXCLUDE those still-visible kept turns (under-count) while also including nothing of value above it. The rewind by one makes the raw clock measure exactly the still-live source material. Degradations are ordered: unresolvable `firstKeptEntryId` ⇒ compaction-index boundary (safe over-count direction); no compaction ⇒ full ledger. Memory and compaction entries contribute zero (`isSourceEntry` filter inside `rawTokensAfterIndex`) so old V2 details or malformed memory rows can never inflate the trigger clock.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "rawTokensSinceLastCompaction findLastCompactionIndex entryIndexForId rawTokensAfterIndex firstKeptEntryId", limit: 10 });
```
(Direct tests: `tests/session-ledger-progress.test.ts:133-142` pins the exact arithmetic end-to-end — `rawTokensSinceLastCompaction([raw-1, cmp(firstKept=raw-1), v2obs, raw-2]) === 3` = raw-1 + raw-2, proving both the kept-turn inclusion AND old-memory immunity; fixture builder `tests/fixtures/session.ts:94-109`.)

## Verdict
Adopt the id-resolved, one-below-the-first-kept-turn counting boundary, the ordered degradation ladder (kept-id → compaction-index → whole ledger), and the source-only token filter. Adapt the compaction entry shape to your host. Omit nothing behavioral.
