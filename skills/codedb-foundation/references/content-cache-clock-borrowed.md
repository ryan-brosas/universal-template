<!-- capsule-v2 -->
# ContentCache CLOCK cache with owned/borrowed value duality — how does a snapshot-backed zero-copy cache enforce memory budgets without freeing mmap'd bytes?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How can one fixed-capacity LRU-ish cache hold both heap-owned copies and borrowed mmap views under a byte budget?

## 8-way set-associative CLOCK with byte-budget sweep
**Path/Symbol:** `src/hot_cache.zig:ContentCache` whole-file (slots/probe :36–52, `putImpl` :179–261, in-window eviction :218–246, `evictForBudget` global sweep :267–292).
**Signature:** `put(key,value)` dupes both; `putBorrowed(key,value)` stores the slice as-is with `value_owned=false` — never freed by the cache (caller's mmap must outlive the entry); `DEFAULT_BYTE_BUDGET = 256 MiB`, `DEFAULT_MAX_ENTRY_BYTES = 8 MiB`.
**Data Shape:** Fixed slot array; probe window PROBE_LIMIT=8; per-slot `{key_hash, key, value, generation, ref_bit, present, value_owned}`; monotonic `generation` handed out per write lets callers detect storage replacement; atomic hit/miss/eviction counters.

### Decisive source
```zig
if (own and (value.len > self.max_entry_bytes or value.len > self.byte_budget)) {
    // Too large to cache; drop any stale entry for the key so get()
    // cannot serve outdated content. Search re-reads from disk on miss.
    self.remove(key);
    return;
}
// Window full of other keys — evict in-window (second chance over the
// probe slots) so the new entry stays reachable by get(). A victim from
// a global sweep would strand the entry outside its own window.
```
Budget sweep skips borrowed entries (evicting them frees no budget) and gives ref-bit second chances before eviction.

**Flow:** hash → probe up to 8 slots → update-in-place if found (compute new value BEFORE freeing old so a failed dupe leaves the slot intact) → else first-empty insert → else CLOCK-evict WITHIN the window (clear all ref bits then take base as last resort) → separately, any owned put over-budget triggers a global sweep-hand pass. Borrowed values (snapshot content section mmaps) bypass dupe and budget accounting entirely.
**Invariant:** A hole inside a key's probe window must not shadow it into duplicate insertion (full-window scan on put). Oversize puts REMOVE the stale entry rather than keeping it. Generations change whenever storage is replaced (test-pinned) — downstream caches key validity off them. External synchronization is the CALLER's job (Explorer holds shared/exclusive mu around all access).
**Probe:** `src/hot_cache.zig` self-tests :388–586 ("basic get/put/remove", "byte budget evicts owned values until the new value fits", "per-entry ceiling refuses oversized values and drops the stale entry", "putBorrowed is zero-copy and never frees the value", "mixed owned/borrowed — transitions and eviction free correctly").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "ContentCache", limit: 10 });
```

## Verdict
Adopt owned/borrowed value duality + in-window CLOCK + exempt-from-budget borrowed semantics for any content cache fronting an mmap-backed store; adapt budgets to your RSS envelope; omit FNV-1a specifics.
