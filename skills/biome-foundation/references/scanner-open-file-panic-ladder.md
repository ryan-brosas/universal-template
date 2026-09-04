<!-- capsule-v2 -->
# Scanner open-file panic ladder — how does one bad file fail without killing a parallel scan?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How should per-file indexing isolate panics and errors so a single hostile file degrades to a diagnostic instead of aborting the traversal?

## catch_unwind + severity downgrade around index_file
**Path/Symbol:** `crates/biome_service/src/scanner.rs:` `open_file` (:821-861), consumed by `ScanContext::handle_path` (:802-805) and `scan_dependencies`' `index_dependency` (:566-592).
**Signature:** `fn open_file<W: WorkspaceScannerBridge>(ctx: &ScanContext<W>, path: BiomePath, trigger: IndexTrigger) -> ModuleDependencies`.
**Data Shape:** input one path; output the file's `ModuleDependencies` (empty on ANY failure); diagnostics emitted as side effect through the context channel.

### Decisive source
```rust
match catch_unwind(|| ctx.workspace.index_file(ctx.project_key, path.clone(), trigger)) {
    Ok(Ok((dependencies, diagnostics))) => {
        for diagnostic in diagnostics {
            ctx.push_diagnostic(diagnostic.with_file_path(path.as_str()));
        }
        dependencies
    }
    Ok(Err(err)) => {
        let mut error: Error = err.into();
        if !path.is_config() && error.severity() >= Severity::Error {
            error = error.with_severity(Severity::Warning).with_file_path(path.as_str());
        }
        ctx.push_diagnostic(error);
        Default::default()
    }
    Err(err) => {   // panicked
        let error = match err.downcast::<String>() {
            Ok(description) => Panic::with_file_and_message(&path, *description),
            Err(err) => match err.downcast::<&'static str>() {
                Ok(description) => Panic::with_file_and_message(&path, *description),
                Err(_) => Panic::with_file(&path),
            },
        };
        ctx.send_diagnostic(error);
        Default::default()
    }
}
```

**Flow:** three-outcome ladder — success (forward deps + stamp each diagnostic with its file path), workspace error (downgrade Error→Warning unless the file is a config file, then keep scanning), panic (downcast payload String→&str→generic into a `Panic` diagnostic). Every outcome returns dependencies, defaulting to empty.
**Invariant:** a scanner worker never propagates a panic or an Err upward; config-file failures KEEP Error severity (a broken `biome.json` must be loud) while ordinary unparseable files are demoted to Warning. The bridge trait therefore requires `RefUnwindSafe`.
**Probe:** `crates/biome_service/src/scanner.tests.rs` — `scanner_doesnt_show_errors_for_inaccessible_files` (:44-81) pins that unreadable files surface at most one non-fatal diagnostic; `scanner_ignored_files_are_not_loaded` (:156-207) pins that scan completion is unaffected by individual files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "catch_unwind Panic with_file_and_message open_file scanner", limit: 10 });
```

## Verdict
Adopt the three-outcome isolation ladder and the config-only severity exemption; adapt `Panic`/`Error` diagnostic constructors to the host's taxonomy; omit the specific downcast set only if the host guarantees unwind payloads. Coverage: path `no_recorded_issue` at pin; no dedicated upstream test asserts the Warning demotion directly (recorded caveat).
