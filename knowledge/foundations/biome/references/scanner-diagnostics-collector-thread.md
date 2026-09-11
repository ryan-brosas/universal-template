<!-- capsule-v2 -->
# Scanner diagnostics collector thread — how do traversal-worker diagnostics reach the caller without deadlocking or leaking noise?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How must a parallel scanner funnel per-file diagnostics from many workers into one ordered result while a verbosity flag controls noise?

## Scoped channel + severity-gated collector
**Path/Symbol:** `crates/biome_service/src/scanner.rs:` `Scanner.scan` (:321-411), `DiagnosticsCollector` (:631-663), `ScanContext.send_diagnostic` (:758-763).
**Signature:** `fn new(verbose: bool) -> Self` (level = Hint if verbose else Error); `fn should_collect(&self, d: &Diagnostic) -> bool`; `fn run(&self, receiver: Receiver<Diagnostic>) -> Vec<Diagnostic>`.
**Data Shape:** `unbounded()` crossbeam channel `(diagnostics_sender, diagnostics_receiver)`; collector runs on one scoped thread named `"biome::scanner"`; `ScanContext.diagnostics_sender: Sender<Diagnostic>` cloned into every traversal worker.

### Decisive source
```rust
let collector = DiagnosticsCollector::new(verbose);
thread::scope(|scope| {
    let handler = thread::Builder::new()
        .name("biome::scanner".to_string())
        .spawn_scoped(scope, || collector.run(diagnostics_receiver))
        .expect("failed to spawn scanner thread");
    let mut ctx = ScanContext { /* ..., diagnostics_sender, ... */ };
    // ... scan_folder + scan_dependencies use ctx ...
    drop(ctx);                       // close the sender BEFORE joining
    let diagnostics = handler.join().unwrap();   // recv() loop ends on channel close
    (duration, diagnostics, configuration_files)
});
```
```rust
fn should_collect(&self, diagnostic: &Diagnostic) -> bool {
    diagnostic.severity() >= self.diagnostic_level || diagnostic.tags().is_internal()
}
fn run(&self, receiver: Receiver<Diagnostic>) -> Vec<Diagnostic> {
    let mut diagnostics = Vec::new();
    while let Ok(diagnostic) = receiver.recv() {   // ends when ALL senders drop
        if self.should_collect(&diagnostic) { diagnostics.push(diagnostic); }
    }
    diagnostics
}
```

**Flow:** create unbounded pair → spawn named collector thread inside `thread::scope` → run traversal with the sender inside ScanContext → drop(ctx) closes the last sender → collector's `recv()` loop terminates → join returns the filtered diagnostics. The WASM variant (`#[cfg(target_family = "wasm")]`, :391-404) skips the thread entirely and comments the ordering constraint: "Close the diagnostics channel before collecting to avoid a deadlock on WASM."
**Invariant:** the sender must outlive all workers and be dropped before `join`; termination is signaled by channel close, never by a count. Severity gate is `>= level OR internal-tag`; non-verbose scans still surface internal diagnostics. Senders use `.send(...).ok()` / `try_send` — a stopped collector must never crash a worker.
**Probe:** `crates/biome_service/src/scanner.tests.rs` — `scanner_doesnt_show_errors_for_inaccessible_files` (:44-81): scanning a directory containing a 0o000 file yields ZERO diagnostics with `verbose: false` and EXACTLY ONE with `verbose: true`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "DiagnosticsCollector should_collect diagnostic_level", limit: 10 });
```

## Verdict
Adopt the scoped-thread + close-then-join channel choreography and the `severity >= level || internal` gate; adapt the severity enum mapping to the host's diagnostic model; omit the WASM branch unless porting to wasm32. Coverage: both paths `no_recorded_issue` at pin.
