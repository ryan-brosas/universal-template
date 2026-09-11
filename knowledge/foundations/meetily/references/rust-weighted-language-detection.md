<!-- capsule-v2 -->
# rust-weighted-language-detection — how are mixed-language transcripts classified and what makes a "Tie" or "LowConfidence"?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the detection algorithm over many transcript chunks, including thresholds, weighting, and the reason taxonomy?

## Char-weighted whatlang voting with five-reason outcome
**Path/Symbol:** `frontend/src-tauri/src/summary/language_detection.rs:detect_summary_language` (:27-79); `summarize_weighted_detection` (:81-115).
**Signature:** `pub(crate) fn detect_summary_language(transcript_texts: &[String]) -> SummaryLanguageDetection` where result = `{language: Option<String>, reason: enum {Detected, Tie, LowConfidence, Unsupported, Empty}}`.
**Data Shape:** Per chunk gate: ≥20 alphabetic chars (`MIN_MEANINGFUL_CHARS`) else skip (never marks seen). Then: whatlang None ⇒ LowConfidence; `!is_reliable() && confidence < 0.25` ⇒ LowConfidence; lang not in the 29-lang map OR mapped code lacks an English prompt name ⇒ Unsupported. Votes accumulate MEANINGFUL CHAR COUNTS per code (not chunk counts), so one long chunk dominates several short ones.

### Decisive source
```rust
if weights.is_empty() {
    return SummaryLanguageDetection {
        language: None,
        reason: if !saw_meaningful_text { Empty }
                else if saw_low_confidence { LowConfidence }
                else if saw_unsupported { Unsupported }
                else { LowConfidence },
    };
}
summarize_weighted_detection(weights)
```

**Flow:** vote → argmax scan; equal top weights ⇒ `Tie` with language=None (caller then falls back to metadata/None rather than guessing). The 29-entry `Lang→code` map is cross-validated against `processor::language_name_from_code` by a test iterating `Lang::all()` (:209-218) so no unsupported code can leak into prompts.
**Invariant:** Reason precedence when nothing detected is fixed: Empty > LowConfidence > Unsupported; tie handling only fires on EXACT weight equality (HashMap iteration order never affects it because comparison is on values).
**Probe:** `grep -cF '+= meaningful_chars;' frontend/src-tauri/src/summary/language_detection.rs` → `1` (battery T37); `grep -c 'SummaryLanguageDetectionReason::Tie' ...language_detection.rs` → `2` (T38); `grep -cF 'Lang::all()' ...language_detection.rs` → `1` (T39).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "detect_summary_language whatlang reliable confidence weighted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt char-weighted voting + explicit reason taxonomy (callers NEED the distinction to log vs fallback correctly); adapt threshold constants and language table; omit serde shape if unused. Direct tests pin English/Chinese/mixed/tie/all-langs cases.
