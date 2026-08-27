<!-- capsule-v2 -->
# BiomePath file-kind priority — how does a path type encode processing order so configs always win?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How can ordering guarantees (configs before manifests before ignore files before handleable files) live in the path type instead of every consumer's sort code?

## Ordinal FileKinds assigned at construction
**Path/Symbol:** `crates/biome_fs/src/path.rs:` `FileKinds` (:32-44), `BiomePath` (:50-59), `priority` (:148-166), `Ord for BiomePath` (:323-330), predicates `is_config/is_manifest/is_ignore/is_handleable/is_required_during_scan` (:169-196); `crates/biome_fs/src/fs.rs:` `ConfigName` (:21-42), `PathKind` (:46-72).
**Signature:** `fn priority(file_name: &str) -> FileKinds`; `fn cmp(&self, other: &Self) -> Ordering { match self.kind.cmp(&other.kind) { Ordering::Equal => self.path.cmp(&other.path), o => o } }`.
**Data Shape:** `BiomePath { path: Utf8PathBuf, kind: FileKinds, was_written: bool, path_kind: PathKind }`; `FileKinds` derives `Ord` with variant order = priority order (doc: "the one on the top has the highest priority"): Config > Manifest > Ignore > Handleable.

### Decisive source
```rust
// crates/biome_fs/src/path.rs :32-44 — variant ORDER is the priority order:
/// A configuration file has the highest priority. It's usually `biome.json` and `biome.jsonc`
Config,
/// It's usually `package.json` and `tsconfig.json`
Manifest,
/// An ignore file, like `.gitignore`
Ignore,
/// A file to handle has the lowest priority. ...
#[default]
Handleable

// :46-48, the BiomePath type doc that consumes this ordinal:
/// This type has its own [Ord] implementation driven by its [FileKinds], where certain files must be inspected
/// before others. For example, configuration files and ignore files must have priority over other files.

fn priority(file_name: &str) -> FileKinds {
    if file_name == ConfigName::biome_json() || file_name == ConfigName::biome_jsonc() {
        FileKinds::Config
    } else if matches!(file_name,
        "package.json" | "tsconfig.json" | "jsconfig.json"
        | "turbo.json" | "turbo.jsonc" | "pnpm-workspace.yaml")
    { FileKinds::Manifest }
    else if matches!(file_name, ".gitignore" | ".ignore") { FileKinds::Ignore }
    else { FileKinds::Handleable }
}
```

**Flow:** both constructors (`new`, `new_with_kind`) derive `kind` from `path.file_name()` AT CONSTRUCTION — classification is intrinsic and cannot be forgotten by a caller. Consumers sort with plain `sort_unstable()` (the pass-17 scanner partition does exactly this) and get configs-first ordering from `Ord`: kind first, lexicographic path tiebreak. `PartialEq`/`Hash` deliberately cover ONLY `(path, kind)` — `was_written`/`path_kind` are metadata, not identity, so hash sets dedup by semantic identity while still distinguishing a config path from a same-named handleable path.
**Invariant:** adding a new manifest/config name means touching exactly one `matches!` arm; the ordinal contract must never be reordered (serde round-trips as a bare string and re-derives kind via `priority`, so on-disk data stays stable). `is_required_during_scan` = Config|Ignore|Manifest is the "scanner must see this even when disabled-ish" superset predicate consumed by service policy.
**Probe:** `crates/biome_fs/src/path.rs` `mod test` (:332-423) — `test_biome_paths` pins per-name classification; `test_biome_file_names_order` + `test_biome_paths_order` pin the Ord outcome after `sort()`. Executed at pin inside `cargo test -p biome_fs --lib`: 12/12 GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "BiomePath FileKinds priority is_config is_manifest sort", limit: 10, fields: ["signature", "lines"] });
```
Observed GREEN retrieval at pin: `BiomePath.priority` Function path.rs :148-166 and the predicate cluster resolve line-exact.

## Verdict
Adopt construction-time kind classification + derived-Ord-as-processing-order as the portable pattern; adapt the concrete name tables (config/manifest lists are product surface) and add host-specific kinds; omit the was_written flag if your host tracks written state elsewhere. Coverage: `no_recorded_issue` at pin; direct tests EXECUTED green.
