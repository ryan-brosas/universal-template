<!-- capsule-v2 -->
# Capability dispatch ladder — routing one operation set across languages without a trait-object registry

**Source:** biome MIT `main@88f805e19b67`; Codebase Memory `biome`. **Question:** How does a polyglot server pick per-language implementations for parse/format/lint/etc. while some languages exist only as embeddings of another?

## Features struct + deprecated-vs-real getters
**Path/Symbol:** `crates/biome_service/src/file_handlers/mod.rs:1150-1175` (`Features` struct of zero-sized handlers), `:1213-1268` (`get_deprecated_capabilities`), `:1270-1300` (`get_real_capabilities`), `:1303-1326` (`is_diagnostic_error`).
**Signature:** `pub(crate) fn get_deprecated_capabilities(&self, language_hint: DocumentFileSource) -> Capabilities`; same shape for `get_real_capabilities`.
**Data Shape:** `Capabilities` is a bag of optional closures per operation (`analyzer.lint`, debug/format/parse...); handlers are unit structs selected by matching `DocumentFileSource`.

### Decisive source
```rust
// :1219-1241 — embedding kinds fork INSIDE the JS arm only in the deprecated getter
DocumentFileSource::Js(source) => match source.as_embedding_kind() {
    JsEmbeddingKind::Astro { .. } => self.astro.capabilities(),
    JsEmbeddingKind::Vue { .. } => self.vue.capabilities(),
    // .svelte.ts / .svelte.js are full JS/TS modules with Svelte semantics;
    // .svelte component documents still use the Svelte handler.
    JsEmbeddingKind::Svelte { file_kind: SvelteFileKind::SourceModule, .. } => self.js.capabilities(),
    JsEmbeddingKind::Svelte { file_kind: SvelteFileKind::Component, .. } => self.svelte.capabilities(),
    JsEmbeddingKind::None => self.js.capabilities(),
},
// :1271-1274 — real getter: ALL JS documents (embeddings included) use js capabilities
DocumentFileSource::Js(_) => self.js.capabilities(),
```
```rust
// :1311-1325 — analyzer severity is CONFIG-resolved for lint/ categories only
let severity = diagnostic.category()
    .filter(|category| category.name().starts_with("lint/"))
    .map_or_else(|| diagnostic.severity(), |category| {
        rules.and_then(|rules| rules.get_severity_from_category(category, diagnostic.severity()))
             .unwrap_or(Severity::Warning)
    });
severity >= Severity::Error
```

**Flow:** caller holds a `DocumentFileSource` (from the db's `file_sources` table) → chooses deprecated getter when it must honor vue/astro/svelte partial support (diagnostics/actions plane), real getter elsewhere → returned `Capabilities` fields are Option closures invoked directly (`capabilities.analyzer.lint` etc.). Feature-gated arms fall back to unknown/js handlers in reduced builds via deliberate `allow(unreachable_patterns)`.
**Invariant:** The two getters MUST stay asymmetric by design (doc warning :1208-1212): removing the embedding fork from the deprecated getter breaks Vue/Astro/Svelte support; using the deprecated getter everywhere pins those handlers onto planes that should treat embedded files as plain JS. Severity is a lookup, not a field: non-lint categories keep intrinsic severity; lint categories default to Warning when unconfigured.
**Probe:** `grep -n 'SvelteFileKind::SourceModule' crates/biome_service/src/file_handlers/mod.rs` → `:1228`; `grep -n 'starts_with("lint/")' crates/biome_service/src/file_handlers/mod.rs` → 2 hits sharing the rules-table lookup: `:558` (result-side severity resolution incl. enforce_assist Error promotion) and `:1313` (`is_diagnostic_error`); `grep -c 'capabilities(&self) -> Capabilities' crates/biome_service/src/file_handlers/*.rs` → one impl per handler file (js/json/css/astro/vue/svelte/html/graphql/grit/md/yaml/ignore/unknown).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Features get_deprecated_capabilities get_real_capabilities", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: struct-of-handlers + capability-closure bags over trait registries (cheap, feature-gated, greppable); keep embedding dispatch isolated in ONE marked-deprecated getter until the embedding graduates. Adapt Capabilities contents to your op set. Omit cfg-matrix fallbacks unless you ship reduced builds.
