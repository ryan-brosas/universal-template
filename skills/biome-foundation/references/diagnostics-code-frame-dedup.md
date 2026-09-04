<!-- capsule-v2 -->
# Code-frame suppression dedup — why does a diagnostic's own location suppress its code frame?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you avoid printing the same source snippet twice when a diagnostic already carries a frame advice?

## FrameVisitor skip_frame protocol
**Path/Symbol:** `crates/biome_diagnostics/src/display.rs:FrameVisitor` (:377-394), consumed by `print_message_advice` (:397-438).
**Signature:** `struct FrameVisitor<'diag> { location: Location<'diag>, skip_frame: bool }`; `fn record_frame(&mut self, location: Location<'_>) -> io::Result<()> { if location == self.location { self.skip_frame = true; } Ok(()) }`; `fn record_backtrace(&mut self, …) { self.skip_frame = true; Ok(()) }`.
**Data Shape:** relies on the deliberate `PartialEq for Location` that compares ONLY `resource == resource && span == span` — `source_code` is EXCLUDED from equality (`crates/biome_diagnostics/src/location.rs:30-38`).

### Decisive source
```rust
// display.rs:430-435 — the implicit frame is emitted only if pass 1 saw
// no explicit frame/backtrace advice at (or equal to) the diagnostic's
// own location
if !skip_frame {
    let location = diagnostic.location();
    if location.span.is_some() {
        visitor.record_frame(location)?;
    }
}
```

**Flow:** pre-pass visits advices → any record_frame whose Location equals the diagnostic's own, or ANY record_backtrace at all, latches `skip_frame` → message phase prints the log line and then synthesizes a code frame ONLY if not skipped.
**Invariant:** Equality MUST ignore source_code or every diagnostic would self-suppress inconsistently (same path+span with differently-borrowed text must still match). Backtraces suppress unconditionally because they subsume the frame's role. A porter comparing full struct equality breaks the dedup silently — duplicated snippets in every rule that adds its own frame.
**Probe:** In-file tests `display.rs:973-995` (`test_header`) pin the rendered single-frame output for a diagnostic WITH location and NO explicit frame advice; `test_frame_advice` :1057-1081 pins explicit-frame rendering at a different location ("other_path") proving non-matching frames are NOT suppressed.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "FrameVisitor", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the two-field visitor + partial-equality contract verbatim. Adapt Location to your diagnostic type but KEEP equality excluding source text. Omit nothing.
