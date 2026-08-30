<!-- capsule-v2 -->
# rust-context-threshold-ladder — how is the chunking threshold chosen per provider, and what are the exact fallback numbers?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** Where does `token_threshold` come from for each LLMProvider, and which constants must a porter reproduce?

## Provider ladder with 300-token prompt reserve
**Path/Symbol:** `frontend/src-tauri/src/summary/service.rs:process_transcript_background` (:393-437).
**Signature:** local `token_threshold: usize` inside `pub async fn process_transcript_background(...)`.
**Data Shape:** Ollama ⇒ live model metadata (`METADATA_CACHE.get_or_fetch`, 5-min TTL global) minus 300; fetch error ⇒ literal `4000`. BuiltInAI ⇒ registry model def minus 300; unknown model ⇒ literal `1748` (2048−300). Cloud + CustomOpenAI ⇒ literal `100000` ("effectively unlimited", single-pass). The same 300 reserve is applied again at chunk time: `chunk_text(text, token_threshold - 300, 100)` — overlap fixed at 100 tokens.

### Decisive source
```rust
} else if provider == LLMProvider::BuiltInAI {
    let model = models::get_model_by_name(&model_name)
        .ok_or_else(|| format!("Unknown model: {}", model_name));
    match model {
        Ok(model_def) => { let optimal = model_def.context_size.saturating_sub(300) as usize; optimal }
        Err(e) => { warn!("{}, using default 2048", e); 1748 }
    }
} else {
    100000
};
```

**Flow:** threshold → single-pass when `(cloud || total_tokens < threshold)` else multi-level chunk/combine → final template fill. Single-pass vs multi-level is decided by this ONE number, so a wrong fallback silently flips small-local-model runs into chunked mode.
**Invariant:** `saturating_sub(300)` appears exactly TWICE (metadata path and built-in path) — keep both or a context_size < 300 underflows to nonsense. Cloud providers never chunk regardless of transcript size.
**Probe:** `grep -cF 'Duration::from_secs(300)' frontend/src-tauri/src/summary/service.rs` → `1` (battery T17, TTL); `grep -cw '1748' ...service.rs` → `1` (T18); `grep -cw '100000' ...service.rs` → `1` (T19); `grep -cF 'saturating_sub(300)' ...service.rs` → `2` (T20).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "token_threshold context_size saturating_sub metadata cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder shape (live-metadata → per-provider static → cloud-unbounded) and the double-300 reserve; adapt constants to your models; omit the ollama `/api/show` metadata client internals. Direct tests absent — constants pinned via battery.
