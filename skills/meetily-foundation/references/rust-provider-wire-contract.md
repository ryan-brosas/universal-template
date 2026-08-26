<!-- capsule-v2 -->
# rust-provider-wire-contract — how does one function serve seven providers with two wire shapes?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** How are endpoint, auth header, request body and response parse selected per provider — and what are the traps?

## Two-shape dispatch: OpenAI-compatible vs Claude messages API
**Path/Symbol:** `frontend/src-tauri/src/summary/llm_client.rs:generate_summary` (:113-333); `LLMProvider::from_str` (:80-91).
**Signature:** `pub async fn generate_summary(client: &Client, provider: &LLMProvider, model_name: &str, api_key: &str, system_prompt: &str, user_prompt: &str, ollama_endpoint: Option<&str>, custom_openai_endpoint: Option<&str>, max_tokens/temperature/top_p: Option<...>, app_data_dir: Option<&PathBuf>, cancellation_token: Option<&CancellationToken>) -> Result<String, String>`.
**Data Shape:** Claude ⇒ POST `/v1/messages` with `x-api-key` + `anthropic-version: 2023-06-01` headers, system as TOP-LEVEL field, HARD-CODED `max_tokens: 2048`, response `content[0].text`. Everyone else (OpenAI/Groq/OpenRouter/Ollama/CustomOpenAI) ⇒ `{base}/v1/chat/completions` (CustomOpenAI: `{endpoint}/chat/completions` with trailing-slash trim), Bearer auth, ChatRequest body; max_tokens/temperature/top_p serialized ONLY for CustomOpenAI (`skip_serializing_if = "Option::is_none"` otherwise). BuiltInAI bypasses HTTP entirely via early return into the llama-helper sidecar.

### Decisive source
```rust
LLMProvider::Claude => {
    header_map.insert("x-api-key", api_key.parse()...);
    header_map.insert("anthropic-version", "2023-06-01".parse()...);
    ("https://api.anthropic.com/v1/messages".to_string(), header_map)
}
...
serde_json::json!(ClaudeRequest { system: system_prompt.to_string(), model: ..., max_tokens: 2048, ... })
```

**Flow:** provider string parse is case-insensitive with aliases (`"builtin-ai" | "local-llama" | "localllama"` ⇒ BuiltInAI); unknown ⇒ Err.
**Invariant (TRAP):** timeout constant is 300s but BOTH timeout error strings say `"LLM request timed out after 60 seconds"` — stale copy; a porter grepping the message will mis-set the deadline. The BuiltInAI match arm after the early return is `unreachable!()` by construction. Request-level timeout rides `.timeout(REQUEST_TIMEOUT_DURATION)` per call on the SHARED client.
**Probe:** `grep -cF 'timed out after 60 seconds' frontend/src-tauri/src/summary/llm_client.rs` → `2` (battery T30); `grep -cF 'Duration::from_secs(300)' ...llm_client.rs` → `1` (T31); `grep -nF 'max_tokens: 2048,' ...llm_client.rs` → line `248` only (T33); `grep -c '/v1/chat/completions' ...llm_client.rs` → `4` (T35).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "generate_summary ClaudeRequest anthropic-version chat/completions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-shape dispatch + option-gated sampling params; adapt endpoints; FIX the stale 60s message when porting (or keep in sync knowingly). Direct tests absent for this module — behavior pinned via battery + live retrieval.
