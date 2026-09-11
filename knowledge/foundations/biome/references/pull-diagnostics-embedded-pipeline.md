<!-- capsule-v2 -->
# Pull-diagnostics pipeline — one request shape covering analyzer runs, parse errors, and embedded snippets

**Source:** biome MIT `main@88f805e19b67`; Codebase Memory `biome`. **Question:** How does an editor-facing diagnostics pull merge rule diagnostics, syntax errors, and languages embedded inside one document without duplicating filter logic?

## pull_diagnostics_for_state
**Path/Symbol:** `crates/biome_service/src/workspace/server.rs:1496-1650` (`WorkspaceServerWithDb::pull_diagnostics_for_state`); state carrier `ProcessFileState` :174-177 (`parsed: ParsedOrigin, file_source: DocumentFileSource, db: WorkspaceDb`).
**Signature:** `fn pull_diagnostics_for_state(&self, params: PullDiagnosticsParams, state: &ProcessFileState, module_db: Rc<dyn ModuleDb>) -> Result<PullDiagnosticsResult, WorkspaceError>`.
**Data Shape:** params: categories/only/skip/enabled_rules/include_code_fix(→pull_code_actions)/inline_config/max_diagnostics/diagnostic_level/enforce_assist; result: `{diagnostics: Vec<SerdeDiagnostic>, errors, warnings, infos, parse_errors, skipped_diagnostics}`.

### Decisive source
```rust
// :1515-1523 — settings query FIRST; missing project is the only hard error
let (working_directory, settings, query_context) = self
    .project_get_settings_query(&state.db, project_key, &path, inline_config)
    .ok_or_else(WorkspaceError::no_project)?;
let capabilities = self.features.get_deprecated_capabilities(state.file_source);
let (diagnostics, ..) = if (categories.is_lint() || categories.is_assist())
    && let Some(lint) = capabilities.analyzer.lint {
// :1573-1602 — embedded snippets re-enter the SAME pipeline with their own language
for embedded_node in state.iter_snippets() {
    let Some(file_source) = embedded_node.file_source(&state.db) else { continue };
    let capabilities = self.features.get_deprecated_capabilities(file_source);
    let Some(lint) = capabilities.analyzer.lint else { continue };
    let results = lint(LintParams { parsed_source: embedded_node.parsed_origin(), /* same filters */ .. });
    diagnostics.extend(results.diagnostics);
    skipped_diagnostics += results.skipped_diagnostics;
    errors += results.errors; warnings += results.warnings; infos += results.infos;
}
// :1611-1626 — non-analyzer branch degrades to severity-filtered parse diagnostics
let mut diagnostics: Vec<_> = state.parsed.serde_diagnostics(&state.db).into_iter()
    .filter(|diagnostic| diagnostic.severity() >= diagnostic_level).collect();
```

**Flow:** resolve settings via salsa query (`no_project` if absent) → pick deprecated capabilities for the DOCUMENT's source → analyzer branch when lint/assist requested AND the language exposes `analyzer.lint` (plugins fetched only for lint categories) → iterate `state.iter_snippets()`: each embedded node resolves its own file_source + capabilities and re-runs lint with IDENTICAL filters, merging all counters → otherwise degrade to parse diagnostics filtered by `diagnostic_level` → at the boundary every diagnostic is stamped `with_file_path(path)`.
**Invariant:** Embedded snippets are first-class diagnostic sources but NEVER change the request's filter set — only their parsed origin and file source differ. Counters (errors/warnings/infos/skipped) are summed across host + snippets so clients see ONE document's totals. Parse errors are reported as `parse_errors` alongside (not instead of) analyzer output. The path rewrite happens exactly once, at projection.
**Probe:** `grep -n 'state.iter_snippets()' crates/biome_service/src/workspace/server.rs` → 4 sites: `:1573`+`:1621` are BOTH inside pull_diagnostics_for_state (analyzer AND parse branch), while `:1306`/`:1469` show sibling ops reusing the same walk; `grep -n 'with_file_path(path.to_string())' crates/biome_service/src/workspace/server.rs` → `:1640` projection site for this op; `grep -c 'ok_or_else(WorkspaceError::no_project)' ...server.rs` → 32 shared sites, this path anchored at `:1515-1517`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "pull_diagnostics_for_state iter_snippets LintParams", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: single pipeline with per-embedded-node re-dispatch, unified counters, and boundary-only path stamping; explicit degradation from analyzer diagnostics to severity-filtered parse diagnostics. Adapt snippet iteration to your embedding model. Omit plugin fetch gating if plugins are always in-process.
