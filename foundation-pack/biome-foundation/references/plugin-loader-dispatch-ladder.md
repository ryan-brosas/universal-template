<!-- capsule-v2 -->
# BiomePlugin::load dispatch — how does one entry point turn a config path into typed analyzer plugins?

**Source:** biome MIT `main@6f7774dc44fc4a6345188f4b81aeaec9da2212c6` (new crate, drift plane pass 13); Codebase Memory `biome`. **Question:** A porter adding plugin support must reproduce the single dispatcher that routes a configured plugin path (bare `.grit`, bare JS/TS file with the feature flag, or manifest directory) into concrete `AnalyzerPlugin` impls — what is the exact precedence and which failure modes are terminal vs. per-rule?

## Dispatch ladder (lib.rs:46-128)
**Path/Symbol:** `crates/biome_plugin_loader/src/lib.rs:46-128` (`BiomePlugin::load`), `:56-67` (.grit fast path), `:70-82` (JS/TS fast path), `:84-87` (manifest existence gate), `:104-125` (manifest rules loop).
**Signature:** `load(fs: Arc<dyn FsWithResolverProxy>, plugin_path: &str, base_path: &Utf8Path, includes: Option<&[NormalizedGlob]>) -> Result<(Self, Utf8PathBuf), PluginDiagnostic>`.
**Data Shape:** Returns `(BiomePlugin { analyzer_plugins: AnalyzerPluginVec }, resolved absolute Utf8PathBuf)`. Every plugin wraps its rules as `Arc<Box<dyn AnalyzerPlugin>>`.

### Decisive source
```rust
// lib.rs:52-58 — path resolution FIRST, then extension sniffing
let plugin_path = normalize_path(&base_path.join(plugin_path));
if plugin_path.extension().is_some_and(|e| e == "grit") {
    let plugin = AnalyzerGritPlugin::load(fs.as_ref(), &plugin_path, includes)?;
    return Ok((Self { analyzer_plugins: vec![Arc::new(Box::new(plugin)) as _] }, plugin_path));
}
```
```rust
// lib.rs:84-87 — directory form requires biome-manifest.jsonc or hard-fails
let manifest_path = plugin_path.join("biome-manifest.jsonc");
if !fs.path_is_file(&manifest_path) {
    return Err(PluginDiagnostic::cant_resolve(manifest_path, None));
}
```

**Flow:** normalize (`base_path.join` + `normalize_path`, no symlink resolution) → ① `.grit` extension ⇒ single-rule Grit plugin, ignore manifest entirely → ② (feature `js_plugin`) `.js|.mjs|.ts|.mts` ⇒ `AnalyzerJsPlugin::load` → ③ otherwise treat as directory: read `biome-manifest.jsonc` with comments allowed (`JsonParserOptions::default().with_allow_comments()`), deserialize `PluginManifest`, then for EACH rule path join under the plugin dir and re-dispatch — but the inner loop only accepts `.grit` (`ends_with(b".grit")` on encoded bytes); anything else raises `unsupported_rule_format`.
**Invariant:** The manifest's rule entries may NOT point at JS plugins even when the `js_plugin` feature is on — only top-level direct file paths reach `AnalyzerJsPlugin`. A porter who "fixes" this by routing manifest rules through the same extension ladder changes the security surface (manifest would auto-load JS code); keep the asymmetry. Also: empty `Some(&[])` includes means "never matches" (doc comment :44-45), NOT "no restriction" — `None` is the unrestricted case.

## Manifest contract (plugin_manifest.rs)
**Path/Symbol:** `crates/biome_plugin_loader/src/plugin_manifest.rs:8-14` + validator `:17-34`.
**Data Shape:** `{ version: u8 (required, validate=supported_version), rules: Vec<PathBuf> }`; version MUST be exactly `1` ("There's only one manifest version now") — v2+ reports a diagnostic and fails deserialization.
**Invariant:** Validation lives in the derive attribute (`#[deserializable(required, validate = "supported_version")]`), not in load() — a porter hand-rolling manifest parsing must replicate both the required-ness AND the value check at deserialize time.

## Direct tests (lib.rs test mod)
**Probe:** `grep -c '#\[test\]' crates/biome_plugin_loader/src/lib.rs` → `7` (5 manifest-path tests + 2 feature-gated JS-plugin tests); `grep -n 'fn load_single_rule_plugin' crates/biome_plugin_loader/src/lib.rs` → `226:`; `grep -n 'Unsupported rule format' crates/biome_plugin_loader/src/lib.rs` → `119:`. Direct tests: `load_plugin` (:162), `load_plugin_without_manifest` (:181), `load_plugin_with_wrong_version` (:192, pins the version gate), `load_plugin_with_wrong_rule_extension` (:209, pins the grit-only manifest rule), `load_single_rule_plugin` (:226).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"BiomePlugin load plugin manifest","limit":5,"detail":"ids"}'
```
→ resolves `biome.crates.biome_plugin_loader.src.lib.load_plugin_without_manifest` / `load_plugin` line-exact.

---
**Verdict:** ADOPT the three-arm ladder verbatim for any host adding declarative plugins; ADAPT paths/globs to your fs abstraction; OMIT the TODO multi-analyser comment (:69) as non-contract.
