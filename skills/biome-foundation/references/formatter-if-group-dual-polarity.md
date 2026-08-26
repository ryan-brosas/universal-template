<!-- capsule-v2 -->
# IfGroupBreaks dual polarity — why does one struct back BOTH if_group_breaks and if_group_fits_on_line, and when does the referenced group need an id?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** A porter implementing Prettier-style conditional content must know exactly how PrintMode polarity maps to the two public constructors and how far the group lookup reaches.

## One struct, two constructors, inverted modes
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:2221-2230` (`if_group_breaks`), `builders.rs:2302-2311` (`if_group_fits_on_line`), `builders.rs:2314-2388` (struct + `with_group_id` + `Format::fmt`).
**Signature:** `if_group_breaks(content) -> IfGroupBreaks { mode: PrintMode::Expanded, .. }`; `if_group_fits_on_line(flat_content) -> IfGroupBreaks { mode: PrintMode::Flat, .. }` — note BOTH return the SAME type `IfGroupBreaks<'_, Context>`.
**Data Shape:** `Condition::new(self.mode).with_group_id(self.group_id)` wrapped in `StartConditionalContent` / `EndConditionalContent` tags; Debug impl prints `IfGroupFitsOnLine` when `mode == Flat`, else `IfGroupBreaks` (:2390-2401).

### Decisive source
```rust
// builders.rs:2380-2388
impl<Context> Format<Context> for IfGroupBreaks<'_, Context> {
    fn fmt(&self, f: &mut Formatter<Context>) -> FormatResult<()> {
        f.write_element(FormatElement::Tag(StartConditionalContent(
            Condition::new(self.mode).with_group_id(self.group_id),
        )))?;
        Arguments::from(&self.content).fmt(f)?;
        f.write_element(FormatElement::Tag(EndConditionalContent))
    }
}
// builders.rs:2321-2323 — the reach rule
/// The referred group must appear before this element in the document
/// but doesn't have to one of its ancestors.
```

**Flow:** constructor picks polarity (Expanded = emit only when group breaks; Flat = emit only when it fits) → `fmt` writes the conditional tag pair carrying mode + optional id → printer resolves against the ENCLOSING group's resolved PrintMode when `group_id` is None, else against the group whose StartGroup carried that id.
**Invariants:** (1) Default without `.with_group_id` refers to the nearest enclosing group — but `fill` wraps EVERY entry in an implicit per-item group, so a trailing-comma conditional inside fill items sees the WRONG (item-local) group unless you thread an explicit id created via `f.group_id("name")` (formatter.rs:47-49) onto BOTH the outer `group(...).with_group_id(...)` AND the conditional — pinned by the worked example at builders.rs:2331-2373 ("The item `[4]` in this example fits on a single line but the trailing comma should still be printed"). (2) Referred group must appear EARLIER in document order; ancestor-hood explicitly not required. (3) Outside any group the content is ALWAYS emitted (:2151).
**Probe:** `grep -n 'mode: PrintMode::Flat,' crates/biome_formatter/src/builders.rs` → `2307:` (fits_on_line); `grep -n 'mode: PrintMode::Expanded,' crates/biome_formatter/src/builders.rs` → `2228:` (breaks); `grep -c 'StartConditionalContent(' crates/biome_formatter/src/builders.rs` → `1`; `grep -n 'Condition::new(self.mode)' crates/biome_formatter/src/builders.rs` → `2383:`; `grep -n 'f.group_id("array")' crates/biome_formatter/src/builders.rs` → `2342:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"IfGroupBreaks Condition PrintMode","limit":6,"detail":"ids"}'
```
Resolves `IfGroupBreaks.fmt Method 2391-2401`, `IfGroupBreaks.with_group_id 2374-2377`, `Struct 2314-2318` line-exact.

## Verdict
Adopt the single-struct/dual-constructor shape (impossible to desync the tag vocabulary from the API surface); adopt the fill-requires-id rule verbatim — it is THE classic wrong port (naive port emits trailing commas per-item or drops them entirely). Adapt Condition/tag naming to host IR. Direct tests: both doc examples at :2155-2167 (flat keeps `,`) and :2268-2299 (expanded drops `,`), plus the group_id fill example :2331-2373 asserting `[1, 234568789, 3456789, [4],]` output.
