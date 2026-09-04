<!-- capsule-v2 -->
# Declarative provider engine factory — how do you add a whole LLM provider as a JSON file instead of Rust code?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** What must a provider definition contain, and through which stages does it become a live boxed Provider without any bespoke code?

## Engine factory plane
**Path/Symbol:** `crates/goose-providers/src/declarative.rs` : `ProviderEngine` (92-101), `DeclarativeProviderConfig` (117-160), `deserialize_provider_config` (267-277), `from_json` (303-320), `load_custom_providers` (285-301); `crates/goose-providers/src/declarative/macros.rs` : `expose_declarative_providers!` (29-44).
**Signature:** `pub fn from_json(json: &str, tls_config: Option<TlsConfig>, key_resolver: impl KeyResolver) -> Result<Box<dyn Provider>>`.
**Data Shape:** `engine ∈ {OpenAI, Ollama, Anthropic}` with serde aliases `openai_compatible|ollama_compatible|anthropic_compatible` plus tolerant FromStr; `requires_auth` DEFAULTS TRUE; `dynamic_models: Option<bool>` tri-state (`Some(false)` + non-empty models ⇒ static-only list, no API call, construction FAILS if models empty; `Some(true)`/`None` ⇒ API-first, fall back to static on endpoint-not-found); setup metadata rejects unknown fields.

### Decisive source
```rust
// Two-phase deserialize: serde bool cannot distinguish absent-vs-false,
// so scan the raw JSON for explicit preserves_thinking BEFORE typing.
let preserves_thinking_was_set = raw.get("preserves_thinking").is_some();
let mut config: DeclarativeProviderConfig = serde_json::from_value(raw)?;
if !preserves_thinking_was_set {
    config.preserves_thinking = should_preserve_thinking_by_default(&config.engine); // true ONLY for OpenAI
}
```
```rust
match config.engine {
    ProviderEngine::OpenAI => openai::from_declarative_config(config, tls_config, key_resolver)
        .map(|provider| Box::new(provider.build()) as Box<dyn Provider>),
    ProviderEngine::Ollama => /* same shape */, ProviderEngine::Anthropic => /* same shape */,
}
```

**Flow:** 45 bundled definitions under `src/declarative/definitions/*.json` embedded via `include_dir!` into `FIXED_PROVIDERS`; `expose_declarative_providers!(alibaba, …, zhipu)` generates one module per provider (`include_str!` JSON const + `create()`) plus `fixed_provider_configs()/entries()`; a parity test pins macro-list == embedded-dir contents. Construction path: parse (two-phase above) → env expansion → engine dispatch → per-engine `from_declarative_config(...).build()`. User-defined providers run through `load_custom_providers(dir)`: missing dir ⇒ empty vec, `.json` filter, parse errors carry the file path.
**Invariant:** Explicitly-set JSON keys always beat engine defaults (the raw-scan exists precisely because a plain `bool` would erase absent-vs-false; groq.json pins an explicit false while every other OpenAI-engine default is true). Guards fail loud at CONSTRUCTION time: `dynamic_models:false` without models bails with the provider name; unknown `setup` fields reject ("unknown field `description`") rather than being silently dropped.
**Probe:** `cargo test -p goose-providers --lib declarative` — 11 passed / 0 failed / 138 filtered out at pin (aliases test, groq-disables-thinking, setup-rejects-unknown-fields, macro↔dir enumeration parity, all-bundled validity incl. unique ids `[a-z0-9_]` first-char grammar, unresolved-at-load, env-default expansion end-to-end, required-env-var bail, ollama static-models return).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "DeclarativeProviderConfig ProviderEngine from_json deserialize_provider_config declarative provider factory", limit: 10, fields: ["lines"] });
// executed live this pass: top hits DeclarativeProviderConfig 117-160, from_json_expands_base_url_from_env_var_default 544-564, provider_engine_deserializes_compatible_aliases 341-371
```

## Verdict
Adopt: definition-as-data with compile-time embedding, engine enum with tolerant aliases, two-phase deserialize for explicit-vs-default booleans, fail-loud construction guards, macro-enumerated bundled set with a parity test. Adapt the field vocabulary (models/pricing/setup metadata shapes) to your host. Omit goose's ModelInfo/canonical-filtering coupling and its specific provider roster.
