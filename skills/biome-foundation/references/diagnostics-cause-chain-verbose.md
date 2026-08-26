<!-- capsule-v2 -->
# Cause-chain + verbose-group rendering — how do you print "Caused by:" ladders and opt-in detail without clutter?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How are diagnostic source chains and verbose advices structured so output stays scannable?

## PrintCauseChain + CountAdvices gate
**Path/Symbol:** `crates/biome_diagnostics/src/display.rs:PrintCauseChain` (:442-461), `CountAdvices` (:643-686), `PrintVerboseAdvices` (:689-695), verbose branch in `print_advices` (:360-370), `print_tags_advices` (:626-640).
**Signature:** `let chain = iter::successors(diagnostic.source(), |prev| prev.source());` then per link: `"\n\nCaused by:\n"` + IndentWriter-wrapped message; `struct CountAdvices(usize)` implements Visit counting every record_* variant.
**Data Shape:** chain = linked list via `fn source(&self) -> Option<&dyn Diagnostic>`; verbose group = a single record_group whose Advices impl delegates to `diagnostic.verbose_advices`.

### Decisive source
```rust
// display.rs:450-457 — every cause link is indented one more level, so a
// 3-deep chain reads as nested "Caused by:" blocks
for diagnostic in chain {
    fmt.write_str("\n\nCaused by:\n")?;
    let mut slot = None;
    let mut fmt = IndentWriter::wrap(fmt, &mut slot, true, "  ");
    diagnostic.message(&mut fmt)?;
}
```
```rust
// display.rs:360-370 — the verbose group exists ONLY if at least one
// verbose advice was counted (empty groups would print a bare title)
if verbose {
    let mut counter = CountAdvices(0);
    diagnostic.verbose_advices(&mut counter)?;
    if !counter.is_empty() {
        visitor.record_group(&"Verbose advice", &PrintVerboseAdvices(diagnostic))?;
    }
}
```

**Flow:** message phase prints root message (+chain) as one log advice → user advices → synthesized tag warnings (Fatal → "Biome exited as this error could not be handled…"; INTERNAL → "derived from an internal Biome error…", :631-637) → verbose group last when enabled and non-empty.
**Invariant:** The count-then-print two-phase is mandatory — record_group has no empty-body suppression of its own. Tag warnings are SYNTHESIZED at render time (never stored in diagnostics) keeping the data model minimal. Cause chains re-indent cumulatively, not flat.
**Probe:** In-file tests pin both behaviors: `test_backtrace_advice`/`test_group_advice` (display.rs:1112-1200) for nested indentation; `test_header`+LogAdvices suite :973-1028 pins tag/log ordering.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "PrintCauseChain", limit: 10, fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt count-gated verbose groups + cumulative-indent cause chains verbatim. Adapt wording. Omit nothing.
