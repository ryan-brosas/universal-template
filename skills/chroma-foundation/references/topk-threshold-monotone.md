<!-- capsule-v2 -->
# TopK threshold monotone — How does a k-bound heap expose its pruning threshold to a WAND loop?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** WAND needs "current k-th best score" after every insertion — what heap design returns it with no extra reads?

## TopKHeap
**Path/Symbol:** `rust/index/src/sparse/types.rs:TopKHeap` (:74-123); element type `Score { score, offset }` with REVERSED Ord (:22-68 encode/decode + Score).
**Signature:** `new(k)`, `push(score, offset) -> f32`, `threshold() -> f32`, `into_sorted_vec() -> Vec<Score>`.
**Data Shape:** Wraps `std::collections::BinaryHeap<Score>` (a max-heap over reversed ordering ⇒ min-score element sits at peek). `threshold()` returns `f32::MIN` until the heap reaches capacity.

### Decisive source
```rust
pub fn push(&mut self, score: f32, offset: u32) -> f32 {
    if self.heap.len() < self.k || score > self.threshold() {
        self.heap.push(Score { score, offset });
        if self.heap.len() > self.k {
            self.heap.pop();
        }
    }
    self.threshold()
}

pub fn threshold(&self) -> f32 {
    if self.heap.len() < self.k {
        f32::MIN
    } else {
        self.heap.peek().map(|s| s.score).unwrap_or(f32::MIN)
    }
}
```

**Flow:** push → maybe insert → evict current min if over capacity → RETURN the post-state threshold. The query loop uses that return directly (`threshold = heap.push(cand_scores[ci], doc)`), so the next window's essential-term split and budget cutoffs see the freshest bound without calling threshold() again.
**Invariant:** Heap size never exceeds k; ties in `Score::Ord` break by ascending offset so output order is deterministic; before capacity, pruning must be disabled (`f32::MIN` passes everything).
**Probe:** `/tmp/chroma-p1/probe_battery.py` mx.topk_min anchor; direct tests in-file at `rust/index/src/sparse/types.rs` tests module plus `ms_19_proptest_invariants.rs` heap properties.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "TopKHeap push threshold into_sorted_vec BinaryHeap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the return-threshold-from-push contract — it removes an entire class of stale-bound bugs when porting WAND-family loops; adapt the element type to your scoring; omit base64 dim encoding specifics.
