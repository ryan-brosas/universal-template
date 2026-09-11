<!-- capsule-v2 -->
# rust-builtin-sidecar-provider — how does a local llama.cpp sidecar slot into a multi-provider LLM client?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** How is the BuiltInAI provider wired from generate_summary into the sidecar lifecycle, and what must callers supply?

## Early-return provider with required app_data_dir
**Path/Symbol:** `frontend/src-tauri/src/summary/llm_client.rs:generate_summary` BuiltInAI branch (:135-149); `summary_engine/client.rs` (`init_sidecar_manager` :64-69, `get_sidecar_manager`, `shutdown_sidecar_gracefully` :250-268, `force_shutdown_sidecar`); re-exports in `summary_engine/mod.rs`.
**Signature:** `if provider == &LLMProvider::BuiltInAI { let app_data_dir = app_data_dir.ok_or_else(|| "app_data_dir is required for BuiltInAI provider")?; return crate::summary::summary_engine::generate_with_builtin(app_data_dir, model_name, system_prompt, user_prompt, cancellation_token).await...; }`.
**Data Shape:** Provider string aliases: `"builtin-ai" | "local-llama" | "localllama"`. The sidecar (llama-helper crate) serves local inference; model registry lives in `summary_engine/models.rs` (`get_model_by_name/get_available_models/get_default_model`, each `ModelDef` carries `context_size` feeding rust-context-threshold-ladder). Download/readiness commands (`builtin_ai_*`) are Tauri-command surface re-exported with `__cmd__` shims.

### Decisive source
```rust
pub use client::{generate_with_builtin, is_sidecar_healthy, shutdown_sidecar_gracefully, force_shutdown_sidecar};
```

**Flow:** generate_summary checks BuiltInAI FIRST and returns before any HTTP construction — the later match arm is `unreachable!()`. Service layer resolves app_data_dir from `_app.path().app_data_dir()` and passes it through; cancellation token flows into the sidecar call like HTTP calls.
**Invariant:** Omitting `app_data_dir` is a hard error (not fallback-to-cloud): local-first product contract. Health/shutdown are separate explicit calls (`is_sidecar_healthy`, graceful vs FORCE shutdown), so host apps own sidecar lifetime.
**Probe:** battery T34 pins `unreachable!` == 1 occurrence; retrieval: `search_graph {"query":"LLMProvider from_str BuiltInAI sidecar"}` line-resolves `from_str` + `init_sidecar_manager`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "generate_with_builtin sidecar manager shutdown graceful", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the early-return local-provider pattern + required-data-dir error + separate health/shutdown handles; adapt the sidecar binary to your runtime; omit model-download UX internals. Pinned via battery + live retrieval at pin.
