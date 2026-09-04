<!-- capsule-v2 -->
# SemanticFlavor / Svelte `$store` duality — framework semantics injected at BOTH ends of the pipeline

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you bolt framework-specific reference semantics onto a language resolver without polluting its core?

## One enum, three intervention points, write-vs-read asymmetry
**Path/Symbol:** `crates/biome_js_semantic/src/semantic_model/flavor.rs` whole file — `SemanticFlavor::{Vanilla, Svelte}` derived `From<&JsFileSource>` via embedding kind; `SVELTE_RUNES` const (7 names) + `is_svelte_rune`; `store_reference_name`: single leading `$`, non-empty remainder, NOT starting with `$`, NEVER a rune. Interventions: (1) extractor `maybe_svelte_store_dereference_binding_name` (events.rs :1035-1051 — slices TokenText to strip `$`, re-keying the lookup) + `normalize_svelte_store_write_references` (:1396-1404 rewrites Write→Read before fallback resolution, because `$store = x` updates the store VALUE, it isn't a write TO the binding); (2) builder `resolve_global_name` flavor-aware store fallback (:452-465) + `is_svelte_store_assignment` guard skipping the declared_at index for `$x =` sites (:469-489); (3) model carries flavor for queries (`model.flavor()`).
**Signature:** `store_reference_name(&self, name: &str) -> Option<&str>` — pure string predicate, no allocation; rune names (`$state`, `$props`, …) are excluded BEFORE the strip so runes stay unresolved references.
**Data Shape:** Flavor rides `SemanticModelOptions` (built from JsFileSource) into both `extractor.set_flavor()` and `builder.set_flavor()` — the SAME value must reach both ends or extractor-promoted and builder-classified references disagree.

### Decisive source
```rust
// events.rs, pop_scope fallback:
let fallback_name = self.maybe_svelte_store_dereference_binding_name(&name);
if let Some(fallback_name) = fallback_name {
    // `$store = ...` updates the store value in Svelte; it is not a write to the
    // backing `store` binding, so treat fallback writes as reads.
    normalize_svelte_store_write_references(&mut references);
    ...
// builder.rs, Read/HoistedRead arms:
if !self.is_svelte_store_assignment(range) {
    self.declared_at_by_start.insert(range.start(), binding_id);
}
```

**Flow:** In Svelte files, `$foo` sightings first try the literal name (a real `$foo` binding wins); on miss they retry as `foo`. Writes through the auto-subscription sugar become READS twice-over: normalized pre-resolution AND excluded from `declared_at_by_start` post-resolution so write-sensitive rules never see them as assignments to `foo`. Globals get the same second chance (`$window` → configured global `window`).
**Invariant:** The dereference applies ONLY in the fallback path — an explicit `let $foo` still resolves normally (order: exact → dual → svelte-strip → promote). Rune exclusion must precede stripping (`$state` is not store `state`). Both normalization layers exist because events and builder indexes are keyed independently; fixing only one leaves half-normalized data.
**Probe:** No upstream unit test file targets the Svelte path directly at this pin — coverage caveat; behavior pinned by the #9519-style comment contracts above + module-graph consumers. Deterministic probe: grep asserts `normalize_svelte_store_write_references` has exactly one caller (events.rs :1122).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SemanticFlavor Svelte store_reference_name normalize_svelte_store_write_references is_svelte_store_assignment", limit: 10 });
```

## Verdict
Adopt the flavor-injected-at-both-ends pattern for embeddable-language resolvers; adapt the name grammar ($-strip) to your host framework; omit the write-normalization ONLY if your framework has no assignment-through-dereference syntax.
