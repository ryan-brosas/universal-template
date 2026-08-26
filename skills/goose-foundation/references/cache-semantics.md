<!-- capsule-v2 -->
# Prompt-cache semantics — how do you declare cache policy per (provider, model) so unknown pairs are safe by default, and where must explicit breakpoints land in an OpenAI-style payload?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how do you centralize prompt-cache behavior as a declarative table instead of scattering it through format modules, and what exact placement rule makes Anthropic-style breakpoints correct on OpenAI-shaped chat payloads?

## Declarative (provider, model) → cache-regime table
**Path/Symbol:** `crates/goose-provider-types/src/cache_semantics.rs:CacheSemantics::for_model` (23–46), `apply_chat_payload_breakpoints` (55–90), `mark_last_content_block` (92–113).
**Signature:** `pub fn for_model(provider_name: &str, model_name: &str) -> CacheSemantics`; `pub fn apply_chat_payload_breakpoints(payload: &mut serde_json::Value)`; `enum CacheSemantics { ExplicitBreakpoints { max_breakpoints: usize }, ImplicitTolerant, ImplicitStrict, Uncached }`.
**Data Shape:** pure functions over identifier strings and an OpenAI-style chat payload (`messages` array + optional `tools` array); no I/O, no provider state. Four regimes: caller-placed markers under a budget; implicit longest-matching-prefix reuse (tolerant); byte-exact prefix extension only (strict); no cache.

### Decisive source
```rust
// cache_semantics.rs — the DEFAULT arm is the contract: an unknown pair must be
// safe under every cache semantics, and ImplicitStrict is exactly that.
"openai" | "azure_openai" | "github_copilot" => {
    if is_openai_responses_model(model_name) {
        CacheSemantics::ImplicitStrict     // Responses models extend byte-for-byte only
    } else {
        CacheSemantics::ImplicitTolerant   // chat completions reuse longest matching prefix
    }
}
"snowflake" | "sagemaker_tgi" => CacheSemantics::Uncached,
_ => CacheSemantics::ImplicitStrict,
```

**Flow:** resolve regime from (provider, model) → for ExplicitBreakpoints, `apply_chat_payload_breakpoints` walks `messages` in REVERSE and marks the LAST content block of the first two user messages it can successfully mark (`user_count >= 2` breaks), marks the FIRST `role=="system"` message found in forward order, then inserts `{"cache_control":{"type":"ephemeral"}}` into the LAST tool's `function` object → `mark_last_content_block` promotes a bare string `content` to a one-block `[{"type":"text",...,"cache_control"}]` array, else mutates the final block in place; unmarkable content returns false.
**Invariant:** unknown (provider, model) pairs default to ImplicitStrict, which is safe under every cache; a user message whose content cannot be marked consumes NO breakpoint slot; the system marker lands on the first system message in array order; string content is always promotable, so marking it never fails silently.
**Probe:** `cargo test -p goose-provider-types --lib cache` — observed GREEN 19 passed / 0 failed; in-file: `for_model_resolves_registered_identifiers_and_defaults_to_strict` (10 cases including `some_new_vendor/some-model → ImplicitStrict`), `breakpoints_cover_system_tools_and_last_two_user_messages` (asserts the older user stays unmarked), `array_content_user_messages_get_a_breakpoint`; corroborated at the format layer by `formats::anthropic::tests::cache_breakpoint_placement::*` and `formats::databricks::tests::test_create_request_{claude,non_claude}_*_cache_control`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "CacheSemantics for_model ImplicitStrict ExplicitBreakpoints apply_chat_payload_breakpoints", limit: 12 });
// located: cache_semantics.rs:CacheSemantics::for_model 23-46, apply_chat_payload_breakpoints 55-90;
// consumers: goose-providers/src/{anthropic,openai,openai_compatible,databricks_v2}.rs stream/route_for_model,
// formats/anthropic.rs:AnthropicFormatOptions::for_model 60-84
```

## Verdict
Adopt the four-regime enum with unknown→ImplicitStrict and the reverse-walk placement (last two MARKABLE users + first system + last tool, string-content promotion). Adapt the concrete provider/model tables and the `cache_control` dialect to your host's providers. Omit OpenAI Responses-model detection specifics unless you serve that API surface. Coverage: cache_semantics.rs `no_recorded_issue` + `metadata_match` (FULL index, generation_matches=true); direct tests GREEN.
