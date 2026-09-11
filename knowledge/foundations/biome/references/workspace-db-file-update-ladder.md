<!-- capsule-v2 -->
# File update ladder — Replace vs Setters: one enum that decides identity, plus lock-free shared collections

**Source:** biome MIT `main@88f805e19b67`; Codebase Memory `biome`. **Question:** When an incremental engine stores parsed files as interned entities, when must a file update reuse the existing entity (setters) versus allocate a new one (replace), and how do clones see writes immediately?

## ParsedSourceUpdateMode / ProjectUpdateMode ladders
**Path/Symbol:** `crates/biome_service/src/db/mod.rs:132-136` (`ParsedSourceUpdateMode`), `:138-162` (`ProjectUpdateMode` doc), `:392-416` (`update_or_insert_file`), `:201-220` (`WorkspaceDbData` contract).
**Signature:** `fn update_or_insert_file(&mut self, path, parsed: AnyParse, document_source_index: usize, snippets: Vec<ParsedSnippet>, mode: ParsedSourceUpdateMode) -> ParsedSource`.
**Data Shape:** `ParsedSourceUpdateMode::{Replace, Setters}`; entities are salsa interns (`ParsedSource::new`, `set_parsed/set_document_source_index/set_snippets`).

### Decisive source
```rust
// :400-415 — Setters reuses the entity; Replace reallocates; missing key always inserts
if mode == ParsedSourceUpdateMode::Replace {
    return self.replace_file(path, parsed, document_source_index, snippets);
}
let existing_file = { self.files.pin().get(path).copied() };
if let Some(existing_file) = existing_file {
    existing_file.set_parsed(self).to(parsed);
    existing_file.set_document_source_index(self).to(document_source_index);
    existing_file.set_snippets(self).to(snippets);
    existing_file
} else {
    self.replace_file(path, parsed, document_source_index, snippets)
}
// :146-149 — the documented trap
/// Passing `Setters` from Shared mode can deadlock because Salsa cannot acquire
/// exclusive storage access while the retained shared handle is alive. Passing
/// `Replace` from Owned mode changes the project's Salsa identity and leaves
/// the previous input allocated.
```

**Flow:** caller picks mode at the DbState boundary (fork/Shared ⇒ Replace; canonical Owned inside `OwnedDb::with_setter` ⇒ Setters) → Setters mutates fields of the SAME salsa input (identity preserved, dependents re-run) → Replace allocates a fresh input and repoints the map (old input leaks by design until GC).
**Invariant:** Both storage modes use the same database type, so the mode CANNOT be inferred from the db — it is threaded explicitly (`:140-144`). Collections are `Arc<papaya::HashMap>` handles shared with every clone (`WorkspaceDbData`, :201-212): "an update made through this type is immediately visible to all of them, and no lock is needed" — which is exactly what lets a setter thread and fork readers share one map. `insert_source` dedupes by equality into a `boxcar::Vec` (:227-235) so file-source indexes are stable across forks.
**Probe:** `grep -n 'must not infer it from the' crates/biome_service/src/db/mod.rs` → `:143`; `grep -n 'fn update_or_insert_file' crates/biome_service/src/db/mod.rs` → `:392`; `grep -c 'Arc<HashMap<' crates/biome_service/src/db/mod.rs` → ≥6 (files/modules/file_sources/projects × WorkspaceDb/WorkspaceDbData/SharedWorkspaceDb).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "update_or_insert_file ParsedSourceUpdateMode replace setters", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: explicit update-mode enum chosen at the storage boundary; shared Arc collections for cross-clone visibility; dedup-by-equality interning for auxiliary tables. Adapt entity types to your engine. Omit salsa setter mechanics if writes are copy-on-write already — but then keep the identity-preservation property some other way.
