<!-- capsule-v2 -->
# Declarative base-URL derivation — how do you turn arbitrary user-entered base URLs into (host, base_path) that survive IPv6, userinfo, query strings, and versioned paths?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** Where exactly do scheme repair, authority extraction, and chat-completions path derivation happen — and what must never be mangled?

## Base-URL derivation ladder
**Path/Symbol:** `crates/goose-providers/src/openai.rs` : `ensure_url_scheme` (89-108), URL section of `from_declarative_config` (895-924), `derive_base_path` (958-976) + `ends_with_version_segment` (972-976); contrast `crates/goose-providers/src/ollama.rs` (297-314).
**Signature:** `pub fn ensure_url_scheme(raw_url: &str) -> String`; `pub fn derive_base_path(url_path: &str) -> String`; host split: `let host = url[..url::Position::BeforePath].to_string();`.
**Data Shape:** input = possibly scheme-less, possibly full-path (`…/v1/chat/completions`), possibly versioned (`…/v1`) or bare-host URL string; output = `(host /* scheme://[user[:pass]@]host[:port] */, base_path /* relative, no leading '/' */)` plus optional baked query params.

### Decisive source
```rust
// doc comment: the url crate parses `localhost:1234` as scheme="localhost",
// path="1234" — silently dropping BOTH host and port. Repair before parsing.
let is_local = bare_host == "localhost" || bare_host == "127.0.0.1"
    || bare_host == "0.0.0.0" || bare_host == "::1";
let scheme = if is_local { "http" } else { "https" };
```
```rust
if normalized.is_empty()              { "v1/chat/completions".to_string() }
else if normalized.ends_with("chat/completions") { stripped.to_string() }
else if ends_with_version_segment(normalized)    { format!("{normalized}/chat/completions") }
else                                  { format!("{normalized}/v1/chat/completions") }
```
Base-URL query params ride EVERY request: parsed via `url::form_urlencoded::parse` then `api_client.with_query(params)`.

**Flow:** trim → contains `"://"`? passthrough : prepend http(s) by local-host table (IPv6 bracket handled by splitting on `]` first) → `Url::parse` (failure ⇒ "Invalid base URL '{raw}': {e}") → host = everything BeforePath (PRESERVES userinfo + IPv6 authority) → base_path = explicit `base_path` (leading `/` trimmed) else `derive_base_path(url.path())`. Engine divergences: ollama ALWAYS prefixes http:// for scheme-less input and sets the default port for local hosts; anthropic uses base_url VERBATIM with no derivation.
**Invariant:** Authority text is split once and kept byte-exact — brackets, userinfo, port included; path derivation is idempotent for already-complete URLs (ends-with-chat/completions short-circuit) and adds exactly the missing tail for versioned or bare paths.
**Probe:** `cargo test -p goose-providers --lib ensure_url_scheme` (local→http / remote→https / existing-scheme preserved; 3 passed) + `--lib from_custom_config_preserves` (host stays `http://[::1]:1234` and `https://user:pass@gateway.example`; 2 passed) + `--lib parse_model_ids` sibling ladder style; derive ladder pinned by cerebras/from_custom_config construction tests in the same suite. All GREEN at pin this pass; get_code_snippet(derive_base_path) byte-matched checkout :958–970.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "ensure_url_scheme derive_base_path BeforePath host query params openai base url", limit: 10, fields: ["lines"] });
// executed live this pass: ensure_url_scheme 89-108, parse_openai_base_url 110-135, derive_base_path 958-976 located
```

## Verdict
Adopt: repair-before-parse scheme ladder with a local-host table, single BeforePath authority split, explicit-path-over-derived precedence, four-arm path completion, query-param baking into the client. Adapt the default path constants and the local-host set to your host. Omit goose's per-engine divergence copies (ollama http-always/port-default, anthropic verbatim) unless you also serve those engines — and note they ARE divergences, not shared helpers.
