<!-- capsule-v2 -->
# Gemini thinking config — how do effort levels and budgets map onto the two incompatible Gemini thinking knobs?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** when the user picks a ThinkingEffort (or disables thinking), what `thinkingConfig` do you emit for each Gemini family — and which families cannot be disabled at all?

## get_thinking_config family table
**Path/Symbol:** `crates/goose-provider-types/src/formats/google.rs::get_thinking_config` (:639-718) with `ThinkingLevel` (:609-616) / `ThinkingConfig` (:618-626) / `DEFAULT_THINKING_BUDGET = 8192` (:21).
**Signature:** `fn get_thinking_config(model_config: &ModelConfig, thinking_budget: Option<i32>) -> Option<ThinkingConfig>`.
**Data Shape:** `ThinkingConfig{ thinking_level: Option<Minimal|Low|Medium|High>, thinking_budget: Option<i32>, include_thoughts: bool }`; gemini-3 uses ONLY `thinking_level`, gemini-2.5 uses ONLY `thinking_budget`.

### Decisive source
```rust
if model_config.reasoning == Some(false)
    || model_config.thinking_effort() == Some(ThinkingEffort::Off)
{
    let model_name = model_config.model_name.to_lowercase();
    if model_name.starts_with("gemini-3.5") || model_name.starts_with("gemini-3.6") {
        return Some(ThinkingConfig { thinking_level: Some(ThinkingLevel::Minimal), .. });
    }
    // Gemini 2.5 Flash defaults to dynamic thinking; only an explicit budget
    // of 0 turns it off. Other families can't be disabled, so leave them unset.
    if model_name.starts_with("gemini-2.5-flash") {
        return Some(ThinkingConfig { thinking_budget: Some(0), .. });
    }
    return None;
}
// gemini-3 level ladder:
ThinkingEffort::Off | ThinkingEffort::Low => ThinkingLevel::Low,
ThinkingEffort::Medium if model_name.starts_with("gemini-3-pro") => ThinkingLevel::Low,
ThinkingEffort::Medium => ThinkingLevel::Medium,
ThinkingEffort::High | ThinkingEffort::Max => ThinkingLevel::High,
```

**Flow:** disable request? → 3.5/3.6 clamp to Minimal, 2.5-flash gets explicit budget 0, everything else returns None (cannot be disabled server-side) → enabled path: non-gemini → None; gemini-3 → level ladder with `include_thoughts:true`, no budget; gemini-2.5 → budget from request_param `thinking_budget` else caller fallback else DEFAULT 8192, negative budgets warn-and-replace with the default.
**Invariant:** `None` means "omit thinkingConfig entirely" (never send an empty object); the two knobs are mutually exclusive per family; `include_thoughts:false` accompanies every disable that IS expressible.
**Probe:** `crates/goose-provider-types/src/formats/google.rs::test_get_thinking_config_disabled_reasoning` (:1712-1731 — flash→budget 0, pro→None, 3.5-lite→Minimal); `test_get_thinking_config` (:1734-1815 — Medium on `gemini-3-pro*` → Low, on other gemini-3 → Medium, -1 budget → default, gemini-2.0/gpt-4o → None).

## Request-level wiring
**Path/Symbol:** `formats/google.rs::create_request_with_thinking_budget` (:729-737) consumed by `GoogleProvider.stream` (goose-providers/src/google.rs :179-222) and gcpvertexai/litellm via `formats/mod::create_request` (trace_path inbound, callers_total 7).
**Signature:** `fn create_request_with_thinking_budget(model_config, system, messages, tools, thinking_budget: Option<i32>) -> Result<Value>`.
**Data Shape:** the optional budget parameter exists so provider clients can inject their own default before falling back to 8192.
**Flow:** provider stream → create_request(_with_thinking_budget) → get_thinking_config → GenerationConfig.thinking_config (serde skips None fields).
**Invariant:** max_output_tokens is always serialized (`Some(model_config.max_output_tokens())`) while temperature/thinking_config skip when None.
**Probe:** `test_gemini_3_request_omits_temperature` (:1818-1823) pins serde omission behavior end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "ThinkingLevel thinking_budget get_thinking_config gemini minimal include_thoughts", limit: 8 });
```
Executed live at pin: returned `get_thinking_config` :639-718, `test_get_thinking_config` :1734-1815, `test_get_thinking_config_disabled_reasoning` :1712-1731, `create_request_with_thinking_budget` :729-737.

## Verdict
Adopt the two-knob family split and the "some models cannot be disabled" ladder as a declarative table; adapt the family prefixes and default budget to your catalog; omit the gemini-3-pro Medium→Low special case unless your models share that constraint. Coverage: google.rs no_recorded_issue + metadata_match; direct tests green (35 passed / 0 failed).
