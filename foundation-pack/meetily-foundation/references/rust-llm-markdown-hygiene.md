<!-- capsule-v2 -->
# rust-llm-markdown-hygiene — how is raw LLM markdown sanitized before storage, and how is the meeting name recovered?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What exactly does the cleaner strip, in which order, and what title-extraction rules apply?

## Thinking-tag strip then fence unwrap; H1 = meeting name
**Path/Symbol:** `frontend/src-tauri/src/summary/processor.rs:clean_llm_markdown_output` (:261-281); `extract_meeting_name_from_markdown` (:290-295); `service.rs:strip_title_if_present` (:48-58).
**Signature:** `pub fn clean_llm_markdown_output(markdown: &str) -> String`; `pub fn extract_meeting_name_from_markdown(markdown: &str) -> Option<String>`.
**Data Shape:** Order: (1) remove ALL `<think>...</think>` / `<thinking>...</thinking>` blocks via precompiled dot-all regex `(?s)<think(?:ing)?>.*?</think(?:ing)?>`; (2) trim; (3) if the WHOLE remainder starts with ```` ```markdown\n ```` (or bare ```` ```\n ````) AND ends with ```` ``` ````, splice out the fences. No other transformation — tables, pipes and nested code fences inside survive.

### Decisive source
```rust
const PREFIXES: &[&str] = &["```markdown\n", "```\n"];
const SUFFIX: &str = "```";
for prefix in PREFIXES {
    if trimmed.starts_with(prefix) && trimmed.ends_with(SUFFIX) {
        let content = &trimmed[prefix.len()..trimmed.len() - SUFFIX.len()];
        return content.trim().to_string();
    }
}
```

**Flow:** every generate/translate/normalize pass funnels through this cleaner (`run_markdown_transform` cleans too), so stored `result.markdown` is already clean. Meeting name = FIRST line starting `"# "` with the marker stripped; service strips that leading H1 from the SAVED markdown only when it truly starts with one (`strip_title_if_present` avoids the silent-empty-return of a naive first-line stripper on docs without `#`).
**Invariant:** Fence-unwrap only fires when BOTH ends match — an unterminated fence passes through untouched (deliberate: don't eat content on truncated generations). Regex must stay non-greedy across newlines or multi-think models corrupt output.
**Probe:** `grep -cF '(?s)<think(?:ing)?>.*?</think(?:ing)?>' frontend/src-tauri/src/summary/processor.rs` → `1` (battery T04); `grep -c '0.35' ...processor.rs` → `3` incl. comment (T03).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "clean_llm_markdown_output think fence extract_meeting_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt strip→trim→paired-fence-unwrap order and first-H1 naming; adapt prefixes to your fence dialects; omit nothing. Behavior pinned via battery + prompt tests asserting instruction presence.
