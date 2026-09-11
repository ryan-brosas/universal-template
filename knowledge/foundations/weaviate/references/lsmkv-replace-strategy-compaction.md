<!-- capsule-v2 -->
# Replace-strategy segment merge — c2 wins conflicts, tombstone cleanup at root, arena-stable keys

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How do two sorted segments merge under last-writer-wins semantics, and when may tombstones be dropped?

## compactorReplace.do / writeKeys
**Path/Symbol:** `adapters/repos/db/lsmkv/compactor_replace.go:32-69` (struct), `:109-242` (`do`/`writeKeys`), `:264-305` (`writeIndividualNode`).
**Signature:** `newCompactorReplace(w, c1, c2 *segmentCursorReplaceReusable, level, secondaryIndexCount uint16, cleanupTombstones bool, enableChecksumValidation bool, maxNewFileSize int64, allocChecker, valueTransformer)`.
**Data Shape:** `c1` = older (left), `c2` = newer (right); per-key record: key, value-or-tombstone flag, secondaryKeys; output = dummy header → data keys → indexes → real header seek-back → checksum.

### Decisive source
```go
// c1 is always the older segment, so when there is a conflict c2 wins (replace strategy)
if bytes.Equal(key1, key2) {
    if !(c.cleanupTombstones && errors.Is(err2, lsmkv.Deleted)) {
        ki, err := c.writeIndividualNode(f, offset, res2.primaryKey, res2.value,
            res2.secondaryKeys, errors.Is(err2, lsmkv.Deleted))
        ...
    }
    res1, err1 = c.c1.next(); res2, err2 = c.c2.next()   // advance BOTH on equal keys
    continue
}
if (key1 != nil && bytes.Compare(key1, key2) < 0) || key2 == nil { /* write key1 side */ } else { /* key2 side */ }
...
if c.valueTransformer != nil && !tombstone && len(value) > 0 {
    transformed, err := c.valueTransformer(value); ...   // edit-op rewrite (e.g. drop-vector)
}
keyCopy := c.arena.CopyKey(key)   // cursor REUSES buffers ⇒ kis[] would corrupt without stable copies
```

**Flow:** classic two-way merge over reusable cursors: equal keys emit ONLY the newer (c2) record and advance both cursors; smaller key advances alone. A tombstone in the newest position deletes the key outright — and when merging INTO the root segment (no older segments left that the tombstone could be shadowing, i.e. `cleanupTombstones=true`) even the tombstone row is dropped. Values pass through an optional transformer before hitting disk; index sizes accumulate during the scan so the header needs no second O(N) pass.
**Invariant:** Confusing which cursor is newer inverts every conflict decision — the struct comment pins "c1 always the older". Tombstone dropping is legal ONLY against the root/leftmost merge; elsewhere the tombstone must survive to keep shadowing older segments (bucket option `keepTombstones=false` default). The key arena exists because cursors recycle their internal buffers each `next()` — storing raw cursor memory into the key-index slice corrupts the segment silently.
**Probe:** `grep -n 'c1 is always the older segment' adapters/repos/db/lsmkv/compactor_replace.go` → :33 comment; direct tests `TestBucketCompactionFileName` + strategy suites in `lsmkv/bucket_test.go` (:583) and compactor integration tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "compactorReplace writeKeys merge segments cursor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-way merge semantics incl. root-tombstone cleanup and the value-transformer hook. Adapt cursor/arena to your iterator design. Omit checksum-validation toggles if your format differs.
