<!-- capsule-v2 -->
# Thinking-effort vocabulary and harness capability negotiation — how do you normalize effort levels and negotiate a provider-managed reasoning knob?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how should a portable agent normalize free-form thinking-effort strings, and how does a provider that MANAGES its own reasoning harness advertise/selectable effort options back to the agent?

## ThinkingEffort parsing + ThinkingEffortSupport negotiation
**Path/Symbol:** `crates/goose-provider-types/src/thinking.rs:ThinkingEffort` (305-339), `ThinkingEffortSupport` (358-367), `ThinkingEffortCapability`/`ThinkingEffortOption` (341-356); trait hooks `crates/goose-provider-types/src/base.rs:thinking_effort_support/subscribe_thinking_effort_support/set_thinking_effort` (680-702).
**Signature:** `enum ThinkingEffort { Off, Low, Medium, High, Max }` with `FromStr` aliases `off|disabled|none`, `low`, `medium|med`, `high`, `max|xhigh` (lowercased; unknown ⇒ Err) and lowercase Display; `enum ThinkingEffortSupport { Unspecified, Unsupported, Options(ThinkingEffortCapability) }`; `async fn set_thinking_effort(&self, session_id, value: &str) -> Result<bool>`.
**Data Shape:** a harness advertises `{ option_id, values: [{value,label}], current }`; the agent mirrors it verbatim into the `thinking_effort` session option; providers that don't manage reasoning return Unspecified and callers fall back to the model-name-based path.

### Decisive source
```rust
// thinking.rs — the whole negotiation vocabulary
impl FromStr for ThinkingEffort {
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "off" | "disabled" | "none" => Ok(Self::Off),
            "medium" | "med" => Ok(Self::Medium),
            "max" | "xhigh" => Ok(Self::Max),
            other => Err(format!("unknown thinking effort: '{other}'")),
        }
    }
}
enum ThinkingEffortSupport {
    Unspecified,                       // keep model-name-based path
    Unsupported,                       // manages reasoning, no knob for this model
    Options(ThinkingEffortCapability), // pass through harness-advertised option
}

// base.rs trait contract:
async fn set_thinking_effort(&self, _session_id: &str, _value: &str) -> Result<bool, ProviderError> {
    Ok(false) // Ok(true): provider applied it itself (no provider recreation needed)
}
```
Consumers: `ModelConfig.thinking_effort()` (model.rs 314-317) feeds format layers, e.g. `AnthropicFormatOptions::for_model` disables thinking when `== Some(ThinkingEffort::Off)` (formats/anthropic.rs 68-69).

**Flow:** UI/config string → `ThinkingEffort::from_str` (aliases normalized) → if provider reports `Options(capability)` the agent shows the HARNESS's values verbatim, picks one, calls `set_thinking_effort`: true ⇒ done in place; false ⇒ legacy path (encode effort into request params, e.g. `thinking_budget_tokens` mapping in formats/anthropic.rs 686-706). Async capability changes arrive via the optional `watch::Receiver` subscription.
**Invariant:** parsing never panics (unknown ⇒ Err string); harness-advertised values are mirrored VERBATIM (no client-side renaming); Unspecified ≠ Unsupported (fallback vs explicit no-knob); a provider returning `Ok(false)` obligates the caller to take the legacy path instead of assuming application.
**Probe:** negotiation contract pinned by integration fixture `crates/goose/tests/providers.rs:ProviderFixture::test_thinking_effort` (508-553): asserts `Options(capability)` with non-empty values and `set_thinking_effort(..)` returning true, then completes a real turn — requires live provider credentials, NOT executed here (recorded as evidence pointer, honest block). Parsing/suffix behavior covered in the observed GREEN unit run (551 passed): `model::tests::with_canonical_limits::resolves_after_stripping_reasoning_effort_suffix`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "ThinkingEffort FromStr ThinkingEffortSupport", limit: 5 });
// located: ThinkingEffortSupport 360-367, from_str 317-326, fmt 330-338 (has_more=false, exhaustive page)
```

## Verdict
Adopt the closed effort vocabulary with tolerant aliases, the three-way Unspecified/Unsupported/Options support model, and the boolean `set_thinking_effort` applied-vs-legacy handshake. Adapt alias spellings to your product's config grammar; adapt the watch-channel subscription if your harness has no async capability source. Omit the Anthropic budget-token arithmetic unless you need effort→budget mapping. Coverage: thinking.rs/model.rs `no_recorded_issue`; integration probe blocked on live credentials (deterministic source confirmation used).
