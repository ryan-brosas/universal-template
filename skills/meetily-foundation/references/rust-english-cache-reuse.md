<!-- capsule-v2 -->
# rust-english-cache-reuse — when is a previous English summary reused instead of regenerating pass 1?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What exact conditions gate reuse of the cached English summary, and what fingerprint fields must match?

## Source-fingerprinted cache embedded in the result blob
**Path/Symbol:** `frontend/src-tauri/src/summary/service.rs:SummaryCacheSource/build_summary_cache_source` (:60-122), `extract_cached_english_markdown` (:156-190); `processor.rs:resolve_cached_english` (:18-27).
**Signature:** `fn extract_cached_english_markdown(raw: &str, expected_source: &SummaryCacheSource, requested_language: Option<&str>) -> Result<Option<String>, serde_json::Error>`.
**Data Shape:** The completed `summary_processes.result` JSON is `{markdown, english_cache:{markdown, source: SummaryCacheSource, output_language}}`. `SummaryCacheSource` equality covers TEN fields: transcript FNV fingerprint + custom_prompt FNV + template_id + template_fingerprint (fingerprint of rendered structure+section-instructions) + token_threshold + model_provider + model_name + ollama_endpoint + custom_openai_endpoint + max_tokens/temperature/top_p. ANY field drift ⇒ cache miss ⇒ full regeneration.

### Decisive source
```rust
if cache.source != *expected_source {
    return Ok(None);
}
if cache.output_language.as_deref() == Some(requested_language.as_str()) {
    return Ok(None); // already translated to exactly this language
}
```

**Flow:** build expected source → load prior row (`get_summary_data`; read error or bad JSON degrade to None with a warning, never fail) → extract only when: requested language normalizes (via `language_name_from_code`) to non-English AND cache present AND source equal AND cached language ≠ target AND markdown non-empty → pass 1 skipped entirely (`successful_chunk_count` reported as 1).
**Invariant:** FNV-1a 64-bit over raw bytes, formatted `"{:016x}:{len}"` — length suffix disambiguates hash collisions on same-length text edits; template changes invalidate via `template_cache_fingerprint` even at constant template_id. English/variant targets NEVER use cache (en-GB and en_GB both normalize to "English" ⇒ miss by construction, pinned by tests :825-855).
**Probe:** `grep -cF '0xcbf29ce484222325' frontend/src-tauri/src/summary/service.rs` → `1` (battery T13); `grep -cF '{:016x}:{}' ...service.rs` → `1` (T14); `grep -cF 'SECTION-INSTRUCTIONS' ...service.rs` → `1` (T15).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "stable_text_fingerprint SummaryCacheSource english_cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt result-blob-embedded cache + whole-source structural equality; adapt field set to your params; omit Tauri-specific storage. Direct tests pin the resolve matrix (11 cases).
