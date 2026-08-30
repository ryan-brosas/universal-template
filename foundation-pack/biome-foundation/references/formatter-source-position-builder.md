<!-- capsule-v2 -->
# source_position builder — how are sourcemap markers emitted from rule code, and what two early-outs keep them deduplicated?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A porter adding manual source anchors inside format rules must replicate the gating so markers stay minimal and mode-correct.

## SourcePosition emission guard
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:300-360` (`source_position()` docs+ctor, struct, `Format::fmt`).
**Signature:** `pub const fn source_position(position: TextSize) -> SourcePosition`; fmt gates on `f.source_map_generation()`.
**Data Shape:** unit-ish newtype over `TextSize`; emits `FormatElement::SourcePosition(position)` — an inline element, not a tag pair.

### Decisive source
```rust
// builders.rs:341-359
fn fmt(&self, f: &mut Formatter<Context>) -> FormatResult<()> {
    if f.source_map_generation().is_disabled() {
        return Ok(());                       // 1st early-out: no map, no element
    }
    if let Some(FormatElement::SourcePosition(last_position)) = f.buffer.elements().last()
        && *last_position == self.0
    {
        return Ok(());                       // 2nd early-out: adjacent duplicate
    }
    f.write_element(FormatElement::SourcePosition(self.0))?;
    Ok(())
}
```

**Flow:** rule code sprinkles `source_position(offset)` at meaningful AST boundaries → under enabled generation each becomes an IR marker that the printer converts into SourceMarkers (doc example :314-330 asserts the exact marker list, including the collapsed case where two markers share dest after space removal); under disabled generation NOTHING enters the IR — zero overhead in the no-sourcemap path.
**Invariants:** (1) Deduplication is ADJACENT-only (peeks the buffer's last element): equal positions separated by other elements still emit twice — downstream consumers must tolerate repeats. (2) The disabled path must not even allocate the element — porting it as write-always-then-filter wastes memory and breaks the "no overhead" contract. (3) Marker semantics pair with the transform-source-map kernel capsules (deleted-range algebra, marker re-basing) already mined in pass 11.
**Probe:** `grep -n 'is_disabled()' crates/biome_formatter/src/builders.rs` → `346:`; `grep -c 'SourcePosition(last_position)' crates/biome_formatter/src/builders.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"SourcePosition source map marker","limit":5,"detail":"ids"}'
```
Resolves `builders.SourcePosition` nodes; printer-side conversion lives in `printer/mod.rs` print_element match (search "SourceMarker").

## Verdict
Adopt the dual early-out exactly; adapt TextSize to host offsets. Direct test: doc example :314-330 IS executable doctest material asserting `printed.sourcemap()` equality — treat it as the behavioral spec.
