<!-- capsule-v2 -->
# rust-english-canonical-pivot — why does every summary pass through English, and which action runs for each language combination?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** Given a summary language preference and a detected transcript language, exactly which final-language action executes and what is cached?

## Three-action final-language FSM over an English pivot
**Path/Symbol:** `frontend/src-tauri/src/summary/processor.rs:resolve_final_language_action` (:36-47); `generate_meeting_summary` tail (:526-580).
**Signature:** `fn resolve_final_language_action(summary_language: Option<&str>, detected_transcript_language: Option<&str>) -> FinalLanguageAction`; enum `{ ReturnEnglish, NormalizeEnglish, Translate(&'static str) }`.
**Data Shape:** Pass 1 ALWAYS produces canonical English markdown (every base prompt embeds `ENGLISH_BASE_SUMMARY_INSTRUCTION`: "**Write the summary/report in English regardless of transcript language; non-English prose is invalid.**"). Action table: explicit non-English target ⇒ `Translate(name)`; else target English + detected transcript English ⇒ `ReturnEnglish` (skip LLM call); else (target English, transcript unknown/non-English) ⇒ `NormalizeEnglish`.

### Decisive source
```rust
match summary_language.and_then(language_name_from_code) {
    Some(name) if name != "English" => FinalLanguageAction::Translate(name),
    _ => match detected_transcript_language.and_then(language_name_from_code) {
        Some("English") => FinalLanguageAction::ReturnEnglish,
        _ => FinalLanguageAction::NormalizeEnglish,
    },
}
```

**Flow:** pass-1 English → clean → action dispatch. `Translate` failure HARD-fails the run (`return Err("Translation to {} failed")`). `NormalizeEnglish` SOFT-fails: on any non-cancellation error the ORIGINAL markdown is returned and the error only logged (`english_markdown_after_normalization_result` :60-75) — but cancellation must propagate (`cancelled_english_normalization_is_not_swallowed` test :787).
**Invariant:** `language_name_from_code` maps BCP-47 → English names for prompts (`zh-cn→zh→"Chinese"`, `zh-tw→"Traditional Chinese"` directly, unknown → None ⇒ falls back to the normalize path rather than injecting an ISO code into a prompt). Direct tests pin all four matrix corners (:743-772).
**Probe:** `grep -c 'FinalLanguageAction::NormalizeEnglish' frontend/src-tauri/src/summary/processor.rs` → `4` (battery T06); `grep -c 'en-GB' ...processor.rs` → `3` (T10).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "resolve_final_language_action Translate NormalizeEnglish ReturnEnglish", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the English-pivot + 3-action FSM verbatim (it decouples translation cost from summarization and enables cache reuse); adapt the language name table; omit prompt prose. Direct tests: processor.rs unit suite pins the matrix.
