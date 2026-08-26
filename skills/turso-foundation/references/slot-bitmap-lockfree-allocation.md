<!-- capsule-v2 -->
# AtomicSlotBitmap — how do you allocate from a shared arena without a lock and without double-free?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What bit convention, CAS discipline, and hint policy make a lock-free slot allocator both simple and correct?

## 1 = free bitmap; CAS-retry alloc_one; single-op wait-free free_one
**Path/Symbol:** `core/storage/slot_bitmap.rs:26-41` (`AtomicSlotBitmap`), `alloc_one` :72-116, `free_one` :118-129, model-checked tests :131+.
**Signature:** `pub fn alloc_one(&self) -> Option<u32>` (lock-free); `pub fn free_one(&self, slot: u32)` (wait-free, single `fetch_or`); `n_slots % 64 == 0` asserted at construction.
**Data Shape:** words of `AtomicU64`; **bit 1 = free, 0 = allocated** — the inversion vs typical "allocated" bitmaps is deliberate so `ALL_FREE = u64::MAX` initializes a fresh arena with zero writes. `next_word_hint: AtomicUsize` is explicitly "performance hint... Not correctness-critical".

### Decisive source
```rust
// :118-125 — free path with its self-check:
pub fn free_one(&self, slot: u32) {
    let old = self.words[word_idx].fetch_or(mask, Ordering::Release);
    debug_assert!((old & mask) == 0, "double-free detected for slot {slot}");
// :95-105 — alloc CAS loop retries on the FRESH value:
    match self.words[word_idx].compare_exchange_weak(word, new_word, AcqRel, Acquire) {
        Ok(_) => { /* advance hint only when word became ALL_ALLOCATED */ }
        Err(actual) => { word = actual; }   // retry same word with fresh value
```
The inner `while word != ALL_ALLOCATED` keeps hammering the SAME word until it is exhausted or our CAS wins — contention degrades to retry, never blocking. The hint advances past exhausted words and rewinds when a freed word sits before it (:126-128). `is_free` returns an Acquire snapshot that may be stale by design.

**Flow:** alloc → scan from hint → trailing_zeros picks lowest free bit → CAS clears it | free → fetch_or sets bit + double-free debug_assert.
**Invariant:** exactly one atomic op per free; alloc retry must always consume the CAS's fresh `actual` value (reusing the stale `word` spins forever under contention); hint changes can never affect correctness.
**Probe:** in-file model-checked tests: `alloc_one_exhausts_all`, `free_one_allows_reuse`, plus randomized StdRng runs asserting equivalence against a `Vec<bool>` reference model (`assert_equivalent`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "AtomicSlotBitmap alloc_one free_one", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as-is for fixed-slot arenas (page buffers, frame slots, connection slots). Adapt word width to platform. Omit the hint if your slot counts are small. Coverage caveat: none — property-style model tests are co-located.
