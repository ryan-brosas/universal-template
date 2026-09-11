<!-- capsule-v2 -->
# Explorer lazy-completion flags + snapshot adoption — which invariants gate "the index is complete" and how does a fast-load defer work without lying?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How does an engine restore from a compact snapshot yet guarantee every consumer later sees full-index behavior?

## word_index_complete / symbol_index_complete latches with forced rebuilds at use sites
**Path/Symbol:** `src/explore.zig:Explorer` (`adoptContentSection`/`adoptOutlineSection` :197–206, `rebuildWordIndex` :969, `markWordIndexIncomplete(can_load_from_disk)` :1025, `markSymbolIndexIncomplete` :1048, `ensureSymbolIndex` :1058, `ensureDefTokenIndex` :1104, `persist` gates `wordIndexNeedsPersist`/`wordIndexGenerationToPersist` :1181–1195).
**Signature:** every recall/rank entry point begins: `needs_rebuild = !complete and (contents.len() > 0 or (io != null and root_dir != null))` → rebuild pre-shared-lock (rebuilds take the EXCLUSIVE lock themselves).
**Data Shape:** Snapshot = content section mmap + outlines + trigram postings adopted zero-copy (`putBorrowed`); word index and symbol index deliberately NOT persisted in the fast path — they carry completion flags instead.

### Decisive source
```zig
// #539: ensure the word index — Tier 0's recall source — is populated.
// After a snapshot fast-load it is built lazily ... without this, searchContent's
// recall collapses to the trigram/skip_trigram tiers and a relevant restored
// file can be crowded out of max_results by less-relevant hot files. Runs at
// most once per load — rebuildWordIndex sets word_index_complete = true.
// Must precede the shared lock below: rebuildWordIndex takes the exclusive lock.
```
```zig
// #564: never build (and cache) a graph from a deferred symbol index —
// resolveCallees would see no definitions and the empty graph would be cached forever.
if (!self.symbol_index_complete) return;
```
Persist-side honesty: `wordIndexGenerationToPersist()` returns null unless complete+dirty, so partial states are never serialized as if whole.

**Flow:** load adopts mmap sections + marks indexes incomplete → first consumer of each deferred plane triggers its rebuild exactly once (Tier 0 for words; identifier-shaped queries for symbols; def-token pre-pass for multi-word ranked queries) → completion flips atomically under the exclusive lock → persist only writes planes whose generation proves completeness.
**Invariant:** A deferred plane must NEVER be consumed silently: every read path either forces the build or explicitly degrades (ranking skips the boost). Lazy builds bump search_gen so caches can't straddle completion. The empty-graph-forever bug (#564 family) is the canonical failure a porter must design out.
**Probe:** `src/test_explore.zig` dep-graph/explorer integration suites + "cached deep reads and fuzzy finds invalidate exactly"; `grep -n "_complete" src/explore.zig | head -30` shows the latch lattice; `src/test_snapshot.zig` round-trips incl. "audit: long import specifier round-trips on fast-restore (borrow path preserved)".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", query: "rebuildWordIndex ensureSymbolIndex incomplete", limit: 10 });
```

## Verdict
Adopt explicit completion latches per derived structure with use-site forced builds and honest persistence gating; adapt which planes are deferred to your startup budget; omit the wasm/wasm32 special-casing.
