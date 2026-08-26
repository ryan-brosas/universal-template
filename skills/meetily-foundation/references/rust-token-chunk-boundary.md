<!-- capsule-v2 -->
# rust-token-chunk-boundary — how does token-based chunking avoid splitting words and why char-space math?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** How are chunk_size/overlap (in tokens) converted to windows, and what boundary rules prevent mid-word/mid-sentence cuts?

## Char-space windowing over a char vector with sentence-then-word backoff
**Path/Symbol:** `frontend/src-tauri/src/summary/processor.rs:chunk_text` (:190-252); `rough_token_count` (:175-178).
**Signature:** `pub fn chunk_text(text: &str, chunk_size_tokens: usize, overlap_tokens: usize) -> Vec<String>`; `pub fn rough_token_count(s: &str) -> usize`.
**Data Shape:** Token↔char conversion uses a fixed 0.35 tokens/char heuristic (`chars_per_token = 1.0 / 0.35`, i.e. ~2.85 chars/token). Window advance is `step = chunk_size_chars.saturating_sub(overlap_chars).max(1)` — the `.max(1)` guarantees progress even when overlap ≥ size. Text ≤ one window ⇒ single chunk, no LLM-side splitting.

### Decisive source
```rust
let step = chunk_size_chars.saturating_sub(overlap_chars).max(1);
while start_char < total_chars {
    let end_char = (start_char + chunk_size_chars).min(total_chars);
    ...
    if end_char < total_chars {
        let slice = &text[start_byte..end_byte];
        if let Some(last_period) = slice.rfind(". ") {
            end_byte = start_byte + last_period + 2;
        } else if let Some(last_space) = slice.rfind(' ') {
            end_byte = start_byte + last_space + 1;
        }
    }
```

**Flow:** collect `Vec<char>` FIRST (Unicode-safe indexing; byte offsets recomputed per window via `len_utf8` sums so slicing never panics on multibyte) → cut at last `". "` inside the window, else last space, else hard cut → advance by step → stop when `end_char >= total_chars`.
**Invariant:** Boundary adjustment SHRINKS the current window but the NEXT start still advances by the full unshrunk `step`, so adjusted windows can overlap MORE than requested — harmless because downstream merge is additive (see py-chunk-aggregation-merge for the Python twin that does NOT do boundary snapping at all).
**Probe:** `grep -cF 'saturating_sub(overlap_chars).max(1)' frontend/src-tauri/src/summary/processor.rs` → `1` (battery T01); `grep -cF 'rfind(". ")' ...processor.rs` → `1` (T12).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "chunk_text overlap chars_per_token rfind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt char-vector windowing + `.max(1)` progress guarantee + two-level boundary snap; adapt the 0.35 ratio to your tokenizer; omit nothing portable here. Direct tests absent for chunk_text itself — behavior pinned via deterministic battery.
