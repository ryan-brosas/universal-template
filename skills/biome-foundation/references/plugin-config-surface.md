<!-- capsule-v2 -->
# Plugin config surface — untagged string|object entries, in-place path normalization, and the empty-includes trap

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** What exact shapes does the `"plugins": []` config array accept, and when is normalization applied?

## Untagged dual shape (biome_plugin_loader/src/configuration.rs)
**Path/Symbol:** `crates/biome_plugin_loader/src/configuration.rs:78-87` (enum), `:107-119` (hand-written `Deserializable`), `:122-134` (`PluginWithOptions`).
**Data Shape:** `PluginConfiguration` = `Path(String)` | `PathWithOptions(PluginWithOptions { path: String (required), includes: Option<Vec<NormalizedGlob>> })`; serde `untagged, deny_unknown_fields, rename_all = camelCase`.
**Signature (custom deserializer):** peek `value.visitable_type() == DeserializableType::Str` → Path variant; else → PathWithOptions. This mirrors serde's untagged enum but through biome_deserialize so diagnostics carry ranges.

### Decisive source
```rust
// configuration.rs:24-27 — WHERE relative paths get normalized
/// Normalizes plugin paths in-place.
///
/// For each relative path, this joins it with `base_dir` and normalizes
/// `.` / `..` segments (without resolving symlinks).
pub fn normalize_relative_paths(&mut self, base_dir: &Utf8Path)
```

**Flow:** config parse (untagged) → later, workspace calls `normalize_relative_paths(base_dir)` which mutates BOTH variants' path fields in place — absolute paths skipped untouched (:35-37). `Plugins` newtype derefs to `Vec<PluginConfiguration>` and carries a degenerate `FromStr` that always returns default (:44-50, for env-var style plumbing).
**Invariant:** Normalization does NOT resolve symlinks and happens at settings-merge time, not load time — BiomePlugin::load normalizes AGAIN via `normalize_path(&base_path.join(plugin_path))`, so porters must keep idempotence. `includes` uses `NormalizedGlob` (parse-time normalized); negated globs are legal exclusions (`!**/*.test.ts` doc :131).

## Direct tests (configuration.rs test mod, 7 tests)
**Probe:** `grep -c '#\[test\]' crates/biome_plugin_loader/src/configuration.rs` → `8`; `grep -n 'deserialize_object_missing_path_emits_error' crates/biome_plugin_loader/src/configuration.rs` → `219:`; `grep -n 'without resolving symlinks' crates/biome_plugin_loader/src/configuration.rs` → `27:`; `grep -c 'deny_unknown_fields' crates/biome_plugin_loader/src/configuration.rs` → `3` (Plugins + both variants).
Pinned behaviors: plain string vs object vs object-without-includes deserialization; missing required `path` = error result; mixed list keeps order.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"PluginConfiguration normalize_relative_paths PluginWithOptions","limit":5,"detail":"ids"}'
```

---
**Verdict:** ADOPT the two-shape entry grammar + explicit normalize step; the double-normalization idempotence and symlink non-resolution are contracts.
