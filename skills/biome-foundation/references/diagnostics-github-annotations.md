<!-- capsule-v2 -->
# GitHub Actions annotation emission — how do you encode a diagnostic as a `::error …::` workflow command?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the exact command format, severity mapping, and percent-encoding contract for CI log annotations?

## PrintGitHubDiagnostic + escape_data/escape_property
**Path/Symbol:** `crates/biome_diagnostics/src/display_github.rs:PrintGitHubDiagnostic.fmt` (:13-73), `escape_data` (:86-101), `escape_property` (:104-121).
**Signature:** `fn fmt(&self, fmt: &mut fmt::Formatter<'_>) -> io::Result<()>` emitting `"::{} title={},file={},line={},endLine={},col={},endColumn={}::{}"`; `fn escape_data<S: AsRef<str>>(value: S) -> String`; `fn escape_property<S: AsRef<str>>(value: S) -> String`.
**Data Shape:** severity→command: Error|Fatal→"error", Warning→"warning", Hint|Information→"notice"; title = category name (empty default); span falls back to `TextRange::new(1, 1)` when absent.

### Decisive source
```rust
// display_github.rs:86-101 — DATA escaping is the three-char runner
// contract (% first, then newlines as %0D/%0A); property escaping adds
// ':' and ',' because they delimit the property list itself
for c in value.chars() {
    match c {
        '\r' => result.push_str("%0D"),
        '\n' => result.push_str("%0A"),
        '%' => result.push_str("%25"),
        _ => result.push(c),
    }
}
```

**Flow:** resolve location → no source_code or non-File resource = emit NOTHING (silent skip, :24-33) → compute start/end line+col from SourceFile → render message markup then strip to plain text via markup_to_string → write the single-line workflow command.
**Invariant:** Escapes are ordered `%`-first in spirit — but note the match arms push literal sequences, so correctness comes from covering all five chars; the runner's parser (linked ActionCommand.cs / command.ts refs :88-94) treats %0D%0A as round-trippable. Silent-skip on missing file/source is deliberate: formatter and organize-imports diagnostics have no span anchor yet. endLine/endColumn are always emitted even for point spans.
**Probe:** Deterministic source pin (escape tables above); behavior is exercised upstream through CI runs of biome itself. Coverage caveat: no unit tests in this file.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "PrintGitHubDiagnostic", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the command grammar + dual escape tables verbatim. Adapt severity vocabulary to your host CI if not GitHub. Omit nothing.
