<!-- capsule-v2 -->
# Fill/Join builder tag protocol — how do the two list builders differ in entry tagging, and what does the printer consume?

**Source:** biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** `fill` and `join` both build lists via `entry()/entries()/finish()` — what IR protocol distinguishes them and what must a porter replicate exactly?

## Fill: StartFill envelope + StartEntry around EVERY item AND every separator
**Path/Symbol:** `crates/biome_formatter/src/builders.rs:2854-2914` (`FillBuilder`), `builders.rs:2690-2760` (`JoinBuilder`), `formatter.rs:77-79/:81+` (entry points `f.join()`, `f.fill()`), printer consumer `crates/biome_formatter/src/printer/mod.rs:623-763` (`print_fill_entries`) + `:777-785` (`print_fill_separator`).
**Signature:** `FillBuilder::entry(&mut self, separator: &dyn Format<Context>, entry: &dyn Format<Context>) -> &mut Self`; `JoinBuilder::entry(&mut self, entry: &dyn Format<Context>) -> &mut Self` (separator captured at construction via `with_separator`).
**Data Shape:** fill emits `StartFill` … for each item after the first: `StartEntry + <separator> + EndEntry`, then `StartEntry + <item> + EndEntry` … `EndFill`. join writes NO tags at all — it is a plain element stream where the separator fires only between entries (`if with && has_elements`).

### Decisive source
```rust
// builders.rs:2892-2907 — the first-entry gate lives INSIDE entry()
self.result = self.result.and_then(|_| {
    if self.empty {
        self.empty = false;
    } else {
        self.fmt.write_element(FormatElement::Tag(StartEntry))?;
        separator.fmt(self.fmt)?;
        self.fmt.write_element(FormatElement::Tag(EndEntry))?;
    }
    self.fmt.write_element(FormatElement::Tag(StartEntry))?;
    entry.fmt(self.fmt)?;
    self.fmt.write_element(FormatElement::Tag(EndEntry))
});
```

**Flow:** `f.fill().entry(&soft_line_break_or_space(), &item)...finish()` → items become individually measurable `StartEntry/EndEntry` islands inside a `StartFill` region → printer's `print_fill_entries` tries each item flat, breaks to the next line when it doesn't fit, and prints separators through `print_fill_separator` — this is Prettier's `fill` equivalent. Join is just sequential writing with a between-items separator; the formatter-level fan-in is wide (22 inbound callers on `FillBuilder.entry` across css/js formatters, e.g. css media_query_list, scss map pairs).
**Invariants:** (1) The separator is TAGGED as an entry in fill — a porter who writes the separator bare breaks the printer's flat-measurement of items. (2) First-entry suppression of the separator is stateful (`empty` flag) inside `entry()` itself, not the caller's job. (3) Both builders thread errors via `self.result = self.result.and_then(...)` so post-error calls are no-ops and `finish()` surfaces the FIRST error — never unwrap mid-chain. (4) `#[must_use = "must eventually call finish()"]` (:2693/:2855): dropping without finish silently discards accumulated errors.
**Probe:** `grep -c 'Tag(StartEntry)' crates/biome_formatter/src/builders.rs` → `2`; `grep -c 'Tag(EndEntry)' crates/biome_formatter/src/builders.rs` → `2`; `grep -n 'fn print_fill_entries' crates/biome_formatter/src/printer/mod.rs` → `623:`; `grep -c 'self.result = self.result.and_then' crates/biome_formatter/src/builders.rs` → `4` (join/fill/fill-syntax variants); `grep -n 'fn print_fill_separator' crates/biome_formatter/src/printer/mod.rs` → `777:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"FillBuilder entry finish","limit":8,"detail":"ids"}'
```
Resolves all four `FillBuilder` methods line-exact (new 2863-2871 / entries 2874-2884 / entry 2887-2907 / finish 2910-2913); BM25 query "fill builder entries separator" additionally resolves the printer consumers.

## Verdict
Adopt the tag protocol exactly (envelope tags + per-item AND per-separator entries for fill; zero tags for join); adopt the error-threading ladder shape. Adapt entry representation to host IR but keep separators as tagged peers of items. Direct tests: macros.rs write! doc example pins VecBuffer output ordering; snapshot tests across biome_css_formatter/biome_js_formatter exercise print_fill_entries at scale.
