<!-- capsule-v2 -->
# Declarative env-expansion ladder — how do you ship ONE provider definition that serves many deployments without leaking unresolved placeholders?

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** How should `${PLACEHOLDER}` templates in provider configs resolve against environment/config state, and when must resolution happen?

## Env-expansion + lazy re-resolution plane
**Path/Symbol:** `crates/goose-providers/src/declarative.rs` : `KeyResolver`/`EnvKeyResolver` (193-219), `expand_env_vars` (221-245), `resolve_config` (247-265); agent-side twin `crates/goose/src/config/declarative_providers.rs` : `resolve_config` (380-403), `register_declarative_provider` closures (405-516).
**Signature:** `fn expand_env_vars(template: &str, env_vars: &[EnvVarConfig]) -> Result<String>`; `trait KeyResolver { type Error; fn resolve_key(&self, key: &str) -> Result<String, Self::Error>; }`.
**Data Shape:** `EnvVarConfig{name, required=false, secret=false, primary=Option (defaults to required), description, default}`; placeholders spelled `${NAME}`; any declared var whose name ends `_STREAMING` overrides `supports_streaming`.

### Decisive source
```rust
let value = match std::env::var(&var.name) {
    Ok(value) => value,
    Err(_) => match &var.default {
        Some(default) => default.clone(),
        None if var.required => anyhow::bail!("Required environment variable {} is not set", var.name),
        None => continue,                       // placeholder stays verbatim
    },
};
result = result.replace(&placeholder, &value);
```
```rust
// agent-side twin resolves LAZILY so UI changes after startup apply:
let val: Option<bool> = global_config.get_param::<String>(&var.name).ok()
    .map(|s| s.to_lowercase() == "true")
    .or_else(|| global_config.get_param::<bool>(&var.name).ok())
    .or_else(|| var.default.as_deref().map(|d| d.to_lowercase() == "true"));
```

**Flow:** bundled configs are stored UNRESOLVED (test pins `${` survives `fixed_provider_configs()`); expansion runs inside `config_from_json` at factory time for the crate side, and INSIDE registry instantiation closures on the agent side (each moved closure owns its own cloned config; fixed ⇒ `ProviderType::Declarative`, custom-dir ⇒ `ProviderType::Custom`). A validation test walks base_url/base_path/every header VALUE of all 45 definitions and fails if any placeholder is not declared in `env_vars`.
**Invariant:** Resolution ladder is exactly env → declared default → loud bail when `required` → leave-in-place otherwise (an undeclared-but-unused placeholder must never crash load). Key material never comes from a hard-coded source: `EnvKeyResolver` reads process env; the agent crate injects a `ConfigKeyResolver` over global config instead — resolver choice is dependency-injected at `from_json`/`create` call time.
**Probe:** `cargo test -p goose-providers --lib declarative from_json_expands` (env-default expansion builds a live provider), `… from_json_errors_when_required_env_var_is_missing`, `… fixed_provider_configs_are_unresolved`; consumer side `cargo test -p goose --lib providers::init::tests::test_custom_provider_context_limit_is_applied_from_file` (custom-dir provider registered + normalized). All GREEN at pin this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "expand_env_vars resolve_config env placeholder streaming override KeyResolver declarative", limit: 10, fields: ["lines"] });
// executed live this pass: top hits expand_env_vars family + register_declarative_provider 405-516
```

## Verdict
Adopt: declare→validate-placeholder-totality→expand-late pipeline, the four-arm value ladder, the `_STREAMING` naming convention for boolean overrides, and DI'd key resolvers so hosts swap env-for-secret-store freely. Adapt where values live (process env vs config store) — goose itself keeps TWO resolve copies for exactly that reason; prefer one lazy resolver over the duplication. Omit goose's Config::global coupling.
