<!-- capsule-v2 -->
# Plugin diagnostic taxonomy — seven error variants, severity routing, and the two From-impl gates

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** Which failure modes get distinct diagnostics, and how do foreign errors (Grit compile, Boa JS) funnel into the taxonomy?

## Enum + constructors (biome_plugin_loader/src/diagnostics.rs)
**Path/Symbol:** `crates/biome_plugin_loader/src/diagnostics.rs:16-41` (enum), `:84-122` (four constructors), `:142-207` (five payload structs).
**Data Shape:** `PluginDiagnostic` ∈ { CantResolve, Compile, Deserialization, FileSystem, InvalidManifest, UnsupportedRuleFormat, NotLoaded } — all payloads carry `#[message] #[description] message: MessageAndDescription` + optional `#[serde(skip)] source`, all `category = "plugin", severity = Error`.

### Decisive source
```rust
// :43-52 — Grit compile failures become Compile diagnostics with a FIXED message
impl From<CompileError> for PluginDiagnostic {
    fn from(value: CompileError) -> Self {
        Self::Compile(CompileDiagnostic {
            message: MessageAndDescription::from(
                markup! { "Failed to compile the Grit plugin" }.to_owned(),
            ),
            source: Some(Error::from(value)),   // detail rides in source, not message
        })
    }
}
```

**Flow:** loader errors map via From (FileSystemDiagnostic→FileSystem, DeserializationDiagnostic→Deserialization, SyntaxError→Deserialization with generic "Syntax Error" :78-82) → workspace's `load_plugins` collects them; Error-severity ⇒ hard abort at settings update. `NotLoaded` is the LAZY-consumer variant: raised by PluginCache::get_analyzer_plugins when a config references a plugin that never got cached (:111-121 constructor).
**Invariant:** Two compile funnels keep messages stable: Grit = fixed string + detailed source; JS (`From<boa_engine::JsError>`, feature-gated :54-64) = INTERPOLATED message `"Failed to compile the JS plugin: {err}"` with source=None. Debug/Display both delegate to `description()` (:124-134) so snapshots show prose not variant names.
**Probe:** `grep -c 'severity = Error' crates/biome_plugin_loader/src/diagnostics.rs` → `5`; `grep -n 'Failed to compile the Grit plugin' crates/biome_plugin_loader/src/diagnostics.rs` → `47:`; `grep -c '#\[test\]' crates/biome_plugin_loader/src/diagnostics.rs` → `2`; `grep -n 'Plugin is requested but not loaded' crates/biome_plugin_loader/src/diagnostics.rs` → `115:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"PluginDiagnostic NotLoaded CantResolve InvalidManifest","limit":5,"detail":"ids"}'
```

---
**Verdict:** ADOPT as the error-taxonomy template for any plugin host; note snapshot tests (`snap_diagnostic`) are the upstream verification medium — no assert-based tests here.
